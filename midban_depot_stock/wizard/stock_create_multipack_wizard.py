# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@comunitea.com>$
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
from openerp import models, fields, api, exceptions, _


class StockCreateMultiPack(models.TransientModel):

    _name = 'stock.picking.create.multipack.line'
    wizard_id = fields.Many2one('stock.picking.create.multipack', 'Wizard')
    operation_id = fields.Many2one('stock.pack.operation', 'Operation')
    product_id = fields.Many2one('product.product', 'Product')
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    pack_id = fields.Many2one('stock.quant.package', 'Source package')
    qty = fields.Float('Quantity')
    pack_dest_id = fields.Many2one('stock.quant.package', 'Dest package')


class StockCreateMultiPack(models.TransientModel):

    _name = 'stock.picking.create.multipack'

    line_ids = fields.One2many('stock.picking.create.multipack.line',
                               'wizard_id', 'Lines')

    @api.multi
    def create_multipack(self):
        for line in self.line_ids:
            if line.pack_dest_id:
                line.pack_id.write({'parent_id': line.pack_dest_id.id})
        picking = self.env['stock.picking'].browse(
            self.env.context.get('active_id', False))
        picking.delete_picking_package_operations()
        picking.do_prepare_partial()
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def default_get(self, fields):
        res = super(StockCreateMultiPack, self).default_get(fields)
        res['line_ids'] = []
        picking = self.env['stock.picking'].browse(
            self.env.context.get('active_id', False))
        if not picking:
            return res
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()

        for op in picking.pack_operation_ids:
            line_vals = {
                'product_id': op.product_id.id or op.package_id.product_id.id,
                'operation_id': op.id,
                'lot_id': op.lot_id.id or op.packed_lot_id.id,
                'pack_id': op.package_id.id,
                'qty': op.packed_qty,
            }
            res['line_ids'].append(line_vals)
        return res
