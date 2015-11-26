# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@pexego.es>
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
from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class stock_move(models.Model):

    _inherit = 'stock.move'

    q_note = fields.Many2one('qualitative.note', 'Qualitative Comment',
                             related="procurement_id.sale_line_id.q_note")
    det_note = fields.Char('Details', size=256,
                           related="procurement_id.sale_line_id.detail_note")

    def _get_invoice_line_vals(self, move, partner, inv_type):
        res = super(stock_move, self)._get_invoice_line_vals(move, partner, inv_type)

        if inv_type == 'out_refund' and not move.procurement_id:
            sol_obj = self.env['sale.order.line']
            domain = [
                ('order_id','=', move.picking_id.sale_id.id),
                ('product_id', '=', move.product_id.id),
                ('product_uom_qty', '<=', 0)
            ]
            print domain
            sale_line = False
            sale_lines = sol_obj.search(domain)
            if len(sale_lines):
                sale_line = sale_lines[0]
            print sale_line
            return sale_line

            res['invoice_line_tax_id'] = [(6, 0, [x.id for x in sale_line.tax_id])]
            res['account_analytic_id'] = sale_line.order_id.project_id and sale_line.order_id.project_id.id or False
            res['discount'] = sale_line.discount
            if move.product_id.id != sale_line.product_id.id:
                res['price_unit'] = order.env['product.pricelist'].price_get(
                     [sale_line.order_id.pricelist_id.id],
                    move.product_id.id, move.product_uom_qty or 1.0,
                    sale_line.order_id.partner_id, )[sale_line.order_id.pricelist_id.id]
            else:
                res['price_unit'] = sale_line.price_unit
            #uos_coeff = move.product_uom_qty and move.product_uos_qty / move.product_uom_qty or 1.0
            #res['price_unit'] = res['price_unit'] / uos_coeff
        return res

