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
import openerp.addons.decimal_precision as dp


class StockReturnPickingLine(models.TransientModel):

    _inherit = 'stock.return.picking.line'

    uom_id = fields.Many2one('product.uom', 'UoM', required=True)
    product_uos_qty = fields.Float(
        'Second unit quantity',
        digits_compute=dp.get_precision('Product Unit of Measure'),
        required=True)
    uos_id = fields.Many2one('product.uom', 'Second unit', required=True)

    @api.one
    @api.onchange('quantity')
    def quantity_onchange(self):
        if not self.product_id or not self.uom_id or not self.uos_id:
            self.product_uos_qty = 1
            return
        if self.move_id.picking_id.picking_type_code == 'incoming':
            self.product_uos_qty = self.product_id.uom_qty_to_uoc_qty(
                self.quantity, self.move_id.product_uos.id,
                self.move_id.picking_id.partner_id.id)
        else:
            self.product_uos_qty = self.product_id.uom_qty_to_uos_qty(
                self.quantity, self.move_id.product_uos.id)

    @api.one
    @api.onchange('product_uos_qty')
    def product_uos_qty_onchange(self):
        if not self.product_id or not self.uom_id or not self.uos_id:
            self.quantity = 1
            return
        self.quantity = self.product_id.uos_qty_to_uom_qty(
            self.product_uos_qty, self.uos_id.id)


class StockReturnPicking(models.TransientModel):

    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields):
        res = super(StockReturnPicking, self).default_get(fields)
        if not res.get('product_return_moves', False):
            return res
        for line in res['product_return_moves']:
            move = self.env['stock.move'].browse(line['move_id'])
            product = self.env['product.product'].browse(line['product_id'])
            line['uom_id'] = move.product_uom.id
            if move.picking_id.picking_type_code == 'incoming':
                line['product_uos_qty'] = product.uom_qty_to_uoc_qty(
                    line['quantity'], move.product_uos.id,
                    move.picking_id.partner_id.id)
            else:
                line['product_uos_qty'] = product.uom_qty_to_uos_qty(
                    line['quantity'], move.product_uos.id)
            line['uos_id'] = move.product_uos.id
        return res
