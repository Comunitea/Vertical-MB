# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from datetime import datetime


class manual_transfer_wzd(models.TransientModel):

    _name = 'manual.transfer.wzd'

    prod_line_ids = fields.One2many('transfer.line', 'wzd_id',
                                    'Transfer Products',
                                    domain=[('product_id', '!=', False)])
    pack_line_ids = fields.One2many('transfer.line', 'wzd_id',
                                    'Transfer Packs',
                                    domain=[('product_id', '=', False)])

    @api.multi
    def _create_pick(self):
        """
        Creates a pick of internal type to put all the manual transfers.
        """
        vals = {}
        domain = [('code', '=', 'internal')]
        # Ordered by id to get the default internal transfers
        p_type = self.env['stock.picking.type'].search(domain, limit=1,
                                                       order='id')
        if not p_type:
            raise except_orm(_('Error'), _('Picking type internal not found'))
        vals = {
            'picking_type_id': p_type.id,
            'date': datetime.now(),
            'origin': 'Manual transfer wizard'
        }
        return self.env['stock.picking'].create(vals)

    @api.one
    def do_manual_transfer(self):
        """
        For each item in the wizard we create a stock.pack.operation
        and a move related with the operation. If we want to move a
        multiproduct pack we create a move for each product.
        We search for the required quants for each line and we force it in
        context when we assign the move.
        When the move is done the quants will be recalculed (in the
        _apply_removal_strategy method of stock_quant if we are searching for
        quants with reservation_id in domain we search again with the super and
        we need get the same quants as first time).
        """
        t_move = self.env['stock.move']
        # Create a picking to put the entire transfer of internal type
        pick_obj = self._create_pick()
        for field_o2m in [self.prod_line_ids, self.pack_line_ids]:
            for line in field_o2m:
                # We want to move a entire multiproduct pack, we need to create
                # one move and assign it for each product inside the pack
                if not line.product_id and line.package_id.is_multiproduct:
                    quants_by_product = line.package_id.get_products_quants()
                    for product in quants_by_product:
                        quants_lst = quants_by_product[product]
                        qty = 0
                        for q in quants_lst:
                            qty += q.qty
                        move_vals = line.get_move_vals(pick_obj, product, qty)
                        quants2assign = \
                            line.get_quants_line(forced_quants_list=quants_lst)
                        ctx = self._context.copy()
                        ctx.update({'force_quants_location': quants2assign})
                        move_obj = t_move.with_context(ctx).create(move_vals)
                        move_obj.action_confirm()
                        # Move will be the our calculed quants reserved
                        move_obj.action_assign()
                        if move_obj.state != 'assigned':
                            raise except_orm(_('Error'),
                                             _('Imposible assign the move'))

                        # Move will be the our calculed quants reserved
                        move_obj.action_assign()
                    # Create the operation to move a multiproduct pack
                    op_vals = line.get_operation_vals(pick_obj)
                    self.env['stock.pack.operation'].create(op_vals)
                else:
                    # Get operation and related move
                    ops_vals, move_vals = line.get_move_ops_vals(pick_obj)
                    # Get quants we will reserve for the move and operation
                    quants2assign = line.get_quants_line()
                    ctx = self._context.copy()
                    ctx.update({'force_quants_location': quants2assign})
                    move_obj = t_move.with_context(ctx).create(move_vals)
                    move_obj.action_confirm()
                    # Move will be the our calculed quants reserved
                    move_obj.action_assign()
                    if move_obj.state != 'assigned':
                        raise except_orm(_('Error'),
                                         _('Imposible assign the move'))
                    self.env['stock.pack.operation'].create(ops_vals)
        # pick_obj.do_prepare_partial()
        pick_obj.do_transfer()
        return


class transfer_lines(models.TransientModel):
    _name = 'transfer.line'

    wzd_id = fields.Many2one('manual.transfer.wzd', 'Wizard')
    package_id = fields.Many2one('stock.quant.package', 'Pack')
    product_id = fields.Many2one('product.product', 'Product')
    quantity = fields.Float('Quantity',
                            digits=dp.get_precision('Product Unit of Measure'),
                            default=1.0)
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    src_location_id = fields.Many2one('stock.location', 'From location',
                                      required=True)
    dest_location_id = fields.Many2one('stock.location', 'To location',
                                       required=True)
    do_pack = fields.Selection([('no_pack', 'No Pack'), ('palet', 'Palet'),
                                ('box', 'Box')], 'Do Pack', default='no_pack')

    @api.onchange('package_id')
    @api.multi
    def onchange_package_id(self):
        """ Get source location related with pack"""
        self.src_location_id = self.package_id.location_id.id
        self.lot_id = self.package_id.packed_lot_id.id

    @api.multi
    def get_quants_line(self, forced_quants_list=False):
        """
        Check if required quantity is available in source location,
        No multiproduct packs when we are inside this method
        """
        t_quant = self.env['stock.quant']
        res = []
        line = self[0]  # Is called always line by line
        if forced_quants_list:
            for quant in forced_quants_list:
                res.append((quant, quant.qty))
        else:
            if line.product_id:  # Move products from a pack or alone
                line_qty = line.quantity
                product = line.product_id
            else:  # Move entire packs
                line_qty = line.package_id.packed_qty  # No multiproduct pack
                product = line.package_id.product_id  # No multiproduct pack

            # Search quants to force the assignament later
            domain = [('product_id', '=', product.id),
                      ('location_id', '=', line.src_location_id.id),
                      ('qty', '>', 0.0),
                      ('package_id', '=', line.package_id.id)]
            if line.lot_id:
                domain.append(('lot_id', '=', line.lot_id.id))
            quants_objs = t_quant.search(domain)
            assigned_qty = 0
            for quant in quants_objs:
                if line.quantity > quant.qty:
                    res.append((quant, quant.qty))
                    assigned_qty += quant.qty
                else:
                    res.append((quant, line_qty))
                    assigned_qty += line_qty
            if assigned_qty < line_qty:
                raise except_orm(_('Error'), _('Not enought stock available\
                                 for product %s, and quantity of \
                                 %s units' % (product.name, line_qty)))
        return res

    @api.multi
    def get_move_vals(self, pick_obj, product, qty):
        line = self[0]  # Is called always line by line
        return {
            'name': product.name or '',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uos': product.uom_id.id,
            'product_uom_qty': qty,
            'date': datetime.now(),
            'date_expected': datetime.now(),
            'location_id': line.src_location_id.id,
            'location_dest_id': line.dest_location_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'company_id': self.env.user.company_id.id,
            'picking_type_id': pick_obj.picking_type_id.id,
            'procurement_id': False,
            'origin': pick_obj.origin,
            'invoice_state': 'none',
            'picking_id': pick_obj.id
        }

    @api.multi
    def get_operation_vals(self, pick_obj, product=False, qty=1.0):
        """
        Returns a dictionary with generyc operation of move a entire palet
        if product and qty not specified.
        """
        line = self[0]  # Is called always line by line

        # Create a pack of do_pack type if do_pack is box or palet
        result_pack_id = False
        if line.do_pack != 'no_pack':
            vals = {'pack_type': line.do_pack}
            result_pack_id = self.env['stock.quant.package'].create(vals).id

        return {
            'product_id': product and product.id or False,
            'product_uom_id': product and product.uom_id.id or False,
            'product_qty': qty,
            'package_id': line.package_id.id,
            'lot_id': line.lot_id.id,  # No multiproduct
            'location_id': line.src_location_id.id,
            'location_dest_id': line.dest_location_id.id,
            'result_package_id': result_pack_id,
            'picking_id': pick_obj.id,
        }

    @api.multi
    def get_move_ops_vals(self, pick_obj):
        """
        Returns a op_vals dictionary ready to create a stock.pack.operation
        linked to a pick_obj argument and a list of move_vals ready to create a
        stock.move
        """
        line = self[0]  # Is called always line by line

        op_vals = line.get_operation_vals(pick_obj)

        # Operation to move products without pack or from a pack
        if line.product_id:
            qty = line.quantity
            product = line.product_id
            op_vals = line.get_operation_vals(pick_obj, product=product,
                                              qty=qty)
        # Operation to move entire packs
        else:
            qty = line.package_id.packed_qty  # multiproducts??
            product = line.package_id.product_id  # multiproducts??
            # op_vals['product_qty'] = 1
            op_vals = line.get_operation_vals(pick_obj)
        # The dictionary to create a move
        move_vals = self.get_move_vals(pick_obj, product, qty)
        return op_vals, move_vals
