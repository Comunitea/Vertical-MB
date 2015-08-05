# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp import exceptions
from openerp.tools.translate import _
from datetime import datetime, timedelta
import math
from openerp.addons.midban_issue.issue_generator import issue_generator
import openerp.addons.decimal_precision as dp


issue_gen = issue_generator()


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    midban_operations = fields.Boolean(string='Custom midban operations',
                                       related='picking_id.midban_operations',
                                       readonly=True)

    picking_type_code = fields.Char('Picking code',
                                    related='picking_id.picking_type_code')

    def get_max_qty_to_process(self, r_qty, product):
        """
        Obtain the max qty to put in a pack, first palet units, else the
        maximun number of mantle units, else boxe units, else the r_qty units
        """
        un_ca = product.un_ca
        ca_ma = product.ca_ma
        ma_pa = product.ma_pa

        # box_units = un_ca
        # mantle_units = un_ca * ca_ma
        palet_units = un_ca * ca_ma * ma_pa
        prop_qty = r_qty  # Proposed qty to ubicate
        if r_qty >= palet_units:
            prop_qty = palet_units
        else:
            prop_qty = r_qty
        return prop_qty

    def _create_pack_operation(self, item, located_qty):
        t_pack = self.env['stock.quant.package']
        t_ope = self.env['stock.pack.operation']
        op_vals = {
            'location_id': item.sourceloc_id.id,
            'product_id': item.product_id.id,
            'product_qty': located_qty,
            'product_uom_id': item.product_uom_id.id,
            'location_dest_id': item.destinationloc_id.id,
            'picking_id': self.picking_id.id,
            'lot_id': item.lot_id.id,
            'result_package_id': False,
            'owner_id': item.owner_id.id,
            'date': item.date if item.date else datetime.now(),
        }
        pack_obj = t_pack.create({})
        op_vals['result_package_id'] = pack_obj.id
        t_ope.create(op_vals)
        return True

    def _propose_pack_operations(self, item):
        """
        This method try to get a maximum pack logisic unit and a location for
        it.
        If not space for maximum pack logistic unit we get another lower,
        removing mantle by mantle and trying to find available space.
        If not space for a mantle, location cant be founded and return False
        """
        remaining_qty = item.quantity
        product = item.product_id
        while remaining_qty > 0.0:
            located_qty = self.get_max_qty_to_process(remaining_qty, product)
            if located_qty:
                self._create_pack_operation(item, located_qty)
                remaining_qty -= located_qty
            else:
                remaining_qty = -1
        return remaining_qty == 0.0 and True or False

    @api.multi
    def prepare_package_type_operations(self):
        for op in self.picking_id.pack_operation_ids:
            op.unlink()

        # Get operations for monoproduct packs
        for item in self.item_ids:
            sucess = self._propose_pack_operations(item)
            if sucess:
                self.picking_id.write({'midban_operations': True})
            else:
                raise except_orm(_('Error!'), _('Not enought free space.'))

        if sucess:
            # return self.picking_id.do_enter_transfer_details()
            ctx = {
                'active_model': 'stock.picking',
                'active_ids': [self.picking_id.id],
                'active_id': self.picking_id and self.picking_id.id or False
            }
            vals = {'picking_id': self.picking_id.id}
            wzd_obj = self.with_context(ctx).create(vals)
            return wzd_obj.wizard_view()
        return False

    @api.one
    def do_detailed_transfer(self):
        res = super(stock_transfer_details, self).do_detailed_transfer()
        '''if self.picking_id.cross_dock and self.move_lines and \
                self.move_lines[0].move_dest_id:'''
        related_pick = self.picking_id.move_lines[0].move_dest_id.picking_id
        related_pick.do_prepare_partial()
        related_pick.write({'midban_operations': True})
        return res

    @api.multi
    def wizard_view(self):
        res = super(stock_transfer_details, self).wizard_view()

        if self.picking_id.picking_type_code == 'incoming' and \
                not self.picking_id.midban_operations:
            ref = 'midban_depot_stock.custom_view_transfer_details'
            view = self.env.ref(ref)

            return {
                'name': _('Enter transfer details'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.transfer_details',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': self.ids[0],
                'context': self.env.context,
            }
        elif self.picking_id.picking_type_code == 'incoming' and \
                self.picking_id.midban_operations:
            ref = 'midban_depot_stock.custom_view_transfer_details_2'
            view = self.env.ref(ref)

            return {
                'name': _('Enter transfer details'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.transfer_details',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': self.ids[0],
                'context': self.env.context,
            }
        return res

    @api.model
    def default_get(self, fields):
        """
        Overwrited to get the secondary unit to the item line.
        We get conversions of product model if we are in a outgoing picking
        else we use supplier products model conversions.
        We check if product is variable weight or not
        """
        res = super(stock_transfer_details, self).default_get(fields)

        picking_ids = self._context.get('active_ids', [])
        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing only be done for one picking at a time
            return res

        res['item_ids'] = []    # We calc again the item ids
        picking = self.env['stock.picking'].browse(picking_ids[0])
        supplier_id = picking.partner_id.id

        if not picking.pack_operation_ids:
            picking.do_prepare_partial()

        items = []
        for op in picking.pack_operation_ids:
            prod = op.product_id
            uos_id = op.product_uom_id.id
            uos_qty = op.product_qty
            var_weight = False

            if op.linked_move_operation_ids:
                move = op.linked_move_operation_ids[0].move_id

                uos_id = move.product_uos and move.product_uos.id or uos_id
                if picking.picking_type_code == 'incoming':

                    uos_qty = prod.uom_qty_to_uoc_qty(op.product_qty, uos_id,
                                                      supplier_id)
                    supp = prod.get_product_supp_record(supplier_id)
                    if supp.is_var_coeff:
                        var_weight = True
                elif picking.picking_type_code == 'outgoing':
                    uos_qty = prod.uom_qty_to_uos_qty(op.product_qty, uos_id)
                    if prod.is_var_coeff:
                        var_weight = True
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date,
                'owner_id': op.owner_id.id,
                'uos_qty': uos_qty,  # Calculed and added
                'uos_id': uos_id,     # Calculed and added
                'var_weight': var_weight,     # Calculed and added
            }
            if op.product_id:
                items.append(item)
        res.update(item_ids=items, picking_id=picking.id)
        return res


class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    life_date = fields.Datetime('Caducity date')
    uos_qty = fields.Float('Quantity (S.U.)',
                           digits_compute=dp.
                           get_precision('Product Unit of Measure'))
    uos_id = fields.Many2one('product.uom', 'Second Unit')
    var_weight = fields.Boolean('Variable weight', readonly=True,
                                help='If checked, system will not convert \
                                quantitys beetwen units')
    do_onchange = fields.Boolean('Contros onchange', default=True,
                                 readonly=False)

    @api.multi
    def write(self, vals):
        """
            Cuando se modifica life date, el resto de fechas se establecen con
            life date - (product.life_time - product.campo_time)
        """
        picking = self and self[0].transfer_id.picking_id or False
        if picking and picking.picking_type_code != 'incoming' or not picking:
            return super(stock_transfer_details_items, self).write(vals)
        reason = self.env['issue.reason'].search([('code', '=', 'reason22')])
        if not reason:
            raise exceptions.Warning(_('Issue error'),
                                     _('Code of reason_id does not exist'))
        changed = False
        if vals.get('life_date', False) and vals.get('life_date', False) \
                != self.lot_id.life_date:
            changed = True
        res = super(stock_transfer_details_items, self).write(vals)
        if changed:
            for line in self:
                line.lot_id.life_date = vals.get('life_date')
                life_date = datetime.strptime(line.life_date,
                                              '%Y-%m-%d %H:%M:%S')
                if life_date < datetime.now() + \
                        timedelta(days=line.product_id.limit_time):
                    # Generar incidencia
                    picking_id = line.transfer_id.picking_id
                    issue = self.env['issue'].search(
                        [('res_id', '=', picking_id.id),
                         ('reason_id', '=', reason.id)])
                    if not issue:
                        issue = issue_gen.create_issue(
                            self._cr, self._uid, self._ids,
                            'stock.picking', [picking_id.id], 'reason22',
                            flow='purchase.order,' +
                            str(picking_id.purchase_id.id),
                            origin=picking_id.name)
                        issue = self.env['issue'].browse(issue)
                    self.env['product.info'].create(
                        {'issue_id': issue.id,
                         'product_id': line.product_id.id,
                         'product_qty': line.quantity,
                         'uom_id': line.product_uom_id.id,
                         'lot_id': line.lot_id.id, 'reason_id': reason.id})
                for field in ['use_', 'removal_', 'alert_']:
                    diff_days = line.product_id.life_time - \
                        line.product_id[field + 'time']
                    line.lot_id[field + 'date'] = life_date - \
                        timedelta(days=diff_days)
        return res

    @api.onchange('lot_id')
    def onchange_lot_id(self):
        self.life_date = self.lot_id.life_date

    @api.onchange('uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the quantity field
        """
        variable = self.var_weight
        product = self.product_id
        if product and variable and self.product_uom_id.id == self.uos_id.id:
            self.do_onchange = False
            self.quantity = self.uos_qty

        if product and not variable:
            picking_id = self._context.get('picking_id', [])
            picking = self.env['stock.picking'].browse(picking_id)
            if self.do_onchange:
                supplier_id = picking.partner_id.id
                qty = self.uos_qty
                uoc_id = self.uos_id.id

                conv = product.get_purchase_unit_conversions(qty, uoc_id,
                                                             supplier_id)
                # base, unit, or box
                log_unit = product.get_uom_po_logistic_unit(supplier_id)
                new_quantity = conv[log_unit]
                if new_quantity != self.quantity:
                    self.do_onchange = False
                    self.quantity = conv[log_unit]
            else:
                self.do_onchange = True

    @api.onchange('quantity')
    def product_uos_id_onchange(self):
        """
        We change uos_qty field
        """
        variable = self.var_weight
        product = self.product_id
        if product and variable and self.product_uom_id.id == self.uos_id.id:
            self.do_onchange = False
            self.uos_qty = self.quantiry

        if product and not variable:
            picking_id = self._context.get('picking_id', [])
            picking = self.env['stock.picking'].browse(picking_id)
            if self.do_onchange:
                supplier_id = picking.partner_id.id
                qty = self.quantity
                new_uos_qty = product.uom_qty_to_uoc_qty(qty, self.uos_id.id,
                                                         supplier_id)

                if new_uos_qty != self.uos_qty:
                    self.do_onchange = False
                    self.uos_qty = new_uos_qty
            else:
                self.do_onchange = True
