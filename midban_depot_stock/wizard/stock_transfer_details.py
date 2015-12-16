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
from openerp import models, api, fields, exceptions, _
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
    task_type = fields.Selection([('ubication', 'Ubication',),
                                  ('reposition', 'Reposition'),
                                  ('picking', 'Picking')],
                                 related='picking_id.task_type')

    @api.multi
    def prepare_package_type_operations(self):
        for op in self.picking_id.pack_operation_ids:
            op.unlink()

        self.item_ids.split_in_packs()
        self.picking_id.write({'midban_operations': True})
        ctx = {
            'active_model': 'stock.picking',
            'active_ids': [self.picking_id.id],
            'active_id': self.picking_id and self.picking_id.id or False
        }
        vals = {'picking_id': self.picking_id.id}
        wzd_obj = self.with_context(ctx).create(vals)
        return wzd_obj.wizard_view()

    @api.multi
    def do_detailed_transfer(self):
        # Revisamos para apuntar en todas las operaciones las Uos

        ### CMNT se comenta par arendimiento REVISAR
        # for item in self.item_ids:
        #     item.review_packop()
        res = super(stock_transfer_details, self).do_detailed_transfer()

        # Calculate the operations for the next chained picking
        # related_pick = self.picking_id.move_lines and\
        #                self.picking_id.move_lines[0].move_dest_id and\
        #                self.picking_id.move_lines[0].move_dest_id.picking_id
        # if related_pick:
        #     #### CMNT REVISAR QUITAR  DE AQUI PARA AGILIZAR PISTOLA
        #     related_pick.do_prepare_partial()
        #     related_pick.write({'midban_operations': True})
        if self.picking_id.picking_type_code == 'incoming':
            return {
                'name': _('Print Tags'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': [self.env.ref('midban_depot_stock.create_tag_wizard_view').id],
                'res_model': 'create.tag.wizard',
                'context': "{'active_model': 'stock.picking', 'active_id': %s}" % self.picking_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'res_id': False
            }
        return res

    @api.multi
    def calculate_dest_location(self):
        for op in self.picking_id.pack_operation_ids:
            op.unlink()
        self.picking_id.do_prepare_partial()
        for op in self.picking_id.pack_operation_ids:
            op.assign_location()
        ctx = {
            'active_model': 'stock.picking',
            'active_ids': [self.picking_id.id],
            'active_id': self.picking_id and self.picking_id.id or False
        }
        vals = {'picking_id': self.picking_id.id}
        wzd_obj = self.with_context(ctx).create(vals)
        return wzd_obj.wizard_view()

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
        if len(picking_ids) != 1:
            return res

        res['item_ids'] = []    # We calc again the item ids
        picking = self.env['stock.picking'].browse(picking_ids[0])

        if not picking.pack_operation_ids:
            picking.do_prepare_partial()

        supplier_id = 0
        if picking.picking_type_code == 'incoming' and picking.purchase_id:
            supplier_id = picking.partner_id.id

        items = []
        for op in picking.pack_operation_ids:
            prod = op.product_id
            uos_id = op.product_uom_id.id
            uos_qty = op.product_qty
            var_weight = False

            if supplier_id:
                supp = prod.get_product_supp_record(supplier_id)
                if supp.is_var_coeff:
                    var_weight = True
                product_ref = supp.product_code or False
            else:
                if prod.is_var_coeff:
                    var_weight = True
                product_ref = op.product_id.default_code
            if op.linked_move_operation_ids or (op.uos_id and op.uos_qty):
                if (op.uos_id and op.uos_qty):
                    uos_id = op.uos_id.id
                    uos_qty = op.uos_qty
                else:
                    move = op.linked_move_operation_ids[0].move_id
                    uos_id = move.product_uos.id or uos_id
                    uos_qty = move.product_id.uom_qty_to_uos_qty(op.product_qty,
                                                      uos_id, supplier_id)

            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_ref': product_ref or False,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'life_date': op.lot_id and op.lot_id.life_date or False,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date,
                'owner_id': op.owner_id.id,
                'uos_qty': uos_qty,  # Calculed and added
                'uos_id': uos_id,     # Calculed and added
                'do_onchange': True,     # Calculed and added
                'var_weight': var_weight,     # Calculed and added
                # 'task_type': picking.task_type,
            }
            if op.product_id:
                items.append(item)
            sorted_items = sorted(items, key=lambda p: p['product_ref'])

        res.update(item_ids=sorted_items, picking_id=picking.id)
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
    pack_product_id = fields.Many2one('product.product', 'Pack product',
                                      related='package_id.product_id',
                                      readonly=True)
    pack_uom_qty = fields.Float('Pack qty',
                                related='package_id.packed_qty',
                                readonly=True)
    pack_uom_id = fields.Many2one('product.uom', 'Stock unit',
                                  related='package_id.uom_id',
                                  readonly=True)
    pack_uos_qty = fields.Float('Qty (S.U.)',
                                related='package_id.uos_qty',
                                readonly=True)
    pack_uos_id = fields.Many2one('product.uom', 'Secondary unit',
                                  related='package_id.uos_id',
                                  readonly=True)
    product_ref = fields.Char('Ref.')
    @api.one
    def split_in_packs(self):
        """
            Create the packs with a maximun size of a pallet.
        """
        remaining_qty = self.quantity if not self.var_weight else self.uos_qty
        unique_pack = False
        first_ope = True
        while remaining_qty > 0.0:
            located_qty = self._get_max_pack_quantity(remaining_qty)
            if self.var_weight and located_qty == remaining_qty and first_ope:
                unique_pack = True
            if located_qty:
                self.create_pack_operation(located_qty, one_pack=unique_pack)
                remaining_qty -= located_qty
                first_ope= False
            else:
                break

    @api.multi
    def _get_max_pack_quantity(self, remaining_qty):
        """
            Se calcula la cantidad maxima por paquete en la unidad base,
            y se reajusta en base a la segunda unidad.
        """
        self.ensure_one()
        uom = self.product_uom_id if not self.var_weight else self.uos_id
        palet_units = self.product_id.get_palet_size(uom)
        maximum_quantity = remaining_qty < palet_units and remaining_qty or \
            palet_units
        return maximum_quantity

    @api.one
    def create_pack_operation(self, to_pack_qty, one_pack=False):
        """
        When creating pack operation we set the uos_qty based on the
        sale measures
        """
        # supplier_id = self.transfer_id.picking_id.partner_id.id
        if not self.var_weight:
            pack_uom_qty = to_pack_qty
            if self.quantity == to_pack_qty:
                pack_uos_qty = self.uos_qty
            else:
                pack_uos_qty = \
                    self.product_id.uom_qty_to_uos_qty(to_pack_qty,
                                                       self.uos_id.id)
        else:
            pack_uos_qty = to_pack_qty
            if one_pack:
                pack_uom_qty = self.quantity
            else:
                # pack_uom_qty = \
                #     self.product_id.uos_qty_to_uom_qty(to_pack_qty,
                #                                        self.uos_id.id)
                fac = self.quantity / self.uos_qty
                pack_uom_qty = to_pack_qty * fac

        op_vals = {
            'location_id': self.sourceloc_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'product_qty': pack_uom_qty,
            'uos_qty': pack_uos_qty,
            'uos_id': self.uos_id.id,
            'location_dest_id': self.destinationloc_id.id,
            'picking_id': self.transfer_id.picking_id.id,
            'lot_id': self.lot_id.id,
            'result_package_id': False,
            'owner_id': self.owner_id.id,
            'date': self.date if self.date else datetime.now(),
        }
        pack = self.env['stock.quant.package'].create(
            {
                'uos_qty': pack_uos_qty,
                'uos_id': self.uos_id.id
            })
        op_vals['result_package_id'] = pack.id
        self.env['stock.pack.operation'].create(op_vals)

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
        if not product:
            return
        if variable and self.product_uom_id == self.uos_id:
            self.do_onchange = False
            self.quantity = self.uos_qty

        if not variable:
            print u"Changing"
            picking_id = self._context.get('picking_id', [])
            picking = self.env['stock.picking'].browse(picking_id)
            supplier_id = 0
            if picking.picking_type_code == 'incoming' and picking.purchase_id:
                supplier_id = picking.partner_id.id
            if self.do_onchange:
                qty = self.uos_qty
                # uoc_id = self.uos_id.id
                uos_id = self.uos_id.id

                # conv = product.get_purchase_unit_conversions(qty, uoc_id,
                #                                              supplier_id)
                # base, unit, or box
                # log_unit, log_unit_id = \
                #     product.get_uom_po_logistic_unit(supplier_id)
                # new_quantity = conv[log_unit]

                new_quantity = product.uos_qty_to_uom_qty(qty, uos_id,
                                                          supplier_id)
                if new_quantity != self.quantity:
                    self.do_onchange = False
                    self.quantity = new_quantity
            else:
                self.do_onchange = True

    @api.multi
    def review_packop(self):
        op_vals = {
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'product_qty': self.quantity,
            'uos_qty': self.uos_qty,
            'uos_id': self.uos_id.id,
            'package_id': self.package_id.id,
            'lot_id': self.lot_id.id,
            'location_id': self.sourceloc_id.id,
            'location_dest_id': self.destinationloc_id.id,
            'result_package_id': self.result_package_id.id,
            'date': self.date if self.date else datetime.now(),
            'owner_id': self.owner_id.id,
            'picking_id': self.transfer_id.picking_id.id,
        }
        if self.packop_id:
            self.packop_id.with_context(no_recompute=True).write(op_vals)
        else:
            self.packop_id = self.env['stock.pack.operation'].create(op_vals)

    @api.onchange('quantity')
    def product_uos_id_onchange(self):
        """
        We change uos_qty field
        """
        variable = self.var_weight
        product = self.product_id
        if product and variable and self.product_uom_id.id == self.uos_id.id:
            self.do_onchange = False
            self.uos_qty = self.quantity

        if product and not variable:
            picking_id = self._context.get('picking_id', [])
            picking = self.env['stock.picking'].browse(picking_id)
            supplier_id = 0
            if picking.picking_type_code == 'incoming' and picking.purchase_id:
                supplier_id = picking.partner_id.id
            if self.do_onchange:
                supplier_id = picking.partner_id.id
                qty = self.quantity
                new_uos_qty = product.uom_qty_to_uos_qty(qty, self.uos_id.id,
                                                         supplier_id)

                if new_uos_qty != self.uos_qty:
                    self.do_onchange = False
                    self.uos_qty = new_uos_qty
            else:
                self.do_onchange = True
