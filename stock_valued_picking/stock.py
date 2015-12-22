# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
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
from openerp.addons.decimal_precision import decimal_precision as dp
import time
import logging
_logger = logging.getLogger(__name__)

class stock_picking(models.Model):

    _inherit = "stock.picking"

    amount_untaxed = fields.Float(
        compute='_amount_all', digits_compute=dp.get_precision('Sale Price'),
        string='Untaxed Amount', readonly=True, store=False)
    amount_tax = fields.Float(
        compute='_amount_all', digits_compute=dp.get_precision('Sale Price'),
        string='Taxes', readonly=True, store=False)
    amount_total = fields.Float(
        compute='_amount_all', digits_compute=dp.get_precision('Sale Price'),
        string='Total', readonly=True, store=False)
    amount_gross = fields.Float(
        compute='_amount_all', digits_compute=dp.get_precision('Sale Price'),
        string='amount gross', readonly=True, store=False)
    amount_discounted = fields.Float(
        compute='_amount_all', digits_compute=dp.get_precision('Sale Price'),
        string='Sale price', readonly=True, store=False)
    external_note = fields.Text(
        ' External Notes')

    @api.multi
    #@api.depends('move_lines.price_subtotal')
    def _amount_all(self):
        init_t = time.time()
        for picking in self:
            print "Calcula Picking"
            val1 = 0
            val = 0.0
            if not picking.sale_id or not picking.picking_type_code in ['outgoing', 'incoming']:
                picking.amount_tax = picking.amount_untaxed = \
                    picking.amount_gross = 0.0
                continue
            taxes = amount_gross = amount_untaxed = 0.0
            cur = picking.partner_id.property_product_pricelist \
                and picking.partner_id.property_product_pricelist.currency_id \
                or False
            for line in picking.move_lines:
                if line.product_id.is_var_coeff:
                    price_unit = line.procurement_id.sale_line_id.price_unit
                else:
                    price_unit = line.procurement_id.sale_line_id.price_udv
                price_disc_unit = (price_unit * (1 - (line.discount) / 100.0))
                if line.product_id.is_var_coeff:
                    price = price_disc_unit
                    qty = line.product_uom_qty
                else:
                    price = price_disc_unit
                    qty = line.product_uos_qty
                val1 += line.price_subtotal

                price_unit = line.procurement_id.sale_line_id.price_unit
                quantity = line.product_uom_qty
                sale_line = line.procurement_id.sale_line_id
                if sale_line and line.state != 'cancel':
                    for c in sale_line.tax_id.compute_all(
                            price, qty,
                            line.product_id,
                            sale_line.order_id.partner_id)['taxes']:
                        val += c.get('amount', 0.0)

                    amount_gross += (price_unit * qty)
                else:
                    continue
            if cur:
                picking.amount_tax = cur.round(val)
                picking.amount_untaxed = cur.round(val1)
                picking.amount_gross = cur.round(amount_gross)
            else:
                picking.amount_tax = round(val, 2)
                picking.amount_untaxed = round(val1, 2)
                picking.amount_gross = round(amount_gross, 2)

            picking.amount_total = picking.amount_untaxed + picking.amount_tax
            picking.amount_discounted = picking.amount_gross - \
                picking.amount_untaxed
        _logger.debug("CMNT _amount_all %s", time.time() - init_t)

class stock_move(models.Model):

    _inherit = "stock.move"

    price_subtotal = fields.Float(
        compute='_get_subtotal', string="Subtotal",
        digits=dp.get_precision('Sale Price'), readonly=True,
        store=False)
    order_price_unit = fields.Float(
        compute='_get_subtotal', string="Price unit",
        digits=dp.get_precision('Sale Price'), readonly=True,
        store=False)
    cost_subtotal = fields.Float(
        compute='_get_subtotal', string="Cost subtotal",
        digits=dp.get_precision('Sale Price'), readonly=True,
        store=False)
    margin = fields.Float(
        compute='_get_subtotal', string="Margin",
        digits=dp.get_precision('Sale Price'), readonly=True,
        store=False)
    percent_margin = fields.Float(
        compute='_get_subtotal', string="% margin",
        digits=dp.get_precision('Sale Price'), readonly=True,
        store=False)
    discount = fields.Float(compute='_get_subtotal', string="Disc. (%)",
                            digits=(4, 2), readonly=True, store=False)

    @api.multi
    #@api.depends('product_uom_qty')
    def _get_subtotal(self):
        init_t = time.time()
        for move in self:
            print "Subtotal movimiento"
            if move.procurement_id.sale_line_id:
                cost_price = move.product_id.standard_price or 0.0
                move.discount = move.procurement_id.sale_line_id.discount or \
                    0.0

                #Se comentan las siguientes líneas para que haga el cálculo
                    #siempre contra el precio unitario y no contra el precio de
                    #venta, para que salga igual en la factura que en el albarán

                # if move.product_id.is_var_coeff:
                #     price_unit = move.procurement_id.sale_line_id.price_unit
                # else:
                #     price_unit = move.procurement_id.sale_line_id.price_udv

                if move.product_id.is_var_coeff:
                    price_unit = move.procurement_id.sale_line_id.price_unit
                else:
                    price_unit = move.procurement_id.sale_line_id.price_udv
                price_disc_unit = (price_unit * (1 - (move.discount) / 100.0))
                price = price_disc_unit
                if move.product_id.is_var_coeff:
                    qty = move.product_uom_qty
                else:

                    qty = move.product_uos_qty
                # if move.product_id.is_var_coeff:
                #     move.price_subtotal = price_disc_unit * \
                #         move.product_uom_qty
                #     move.cost_subtotal = cost_price * move.product_uom_qty
                # else:
                #     move.price_subtotal = price_disc_unit * \
                #         move.product_uos_qty
                #     move.cost_subtotal = cost_price * move.product_uos_qty

                move.price_subtotal = price_disc_unit * \
                    move.product_uom_qty
                move.cost_subtotal = cost_price * move.product_uom_qty
                sale_line = move.procurement_id.sale_line_id
                taxes = sale_line.tax_id.compute_all(
                                            price,
                                           qty,
                                    move.product_id,
                                    move.picking_id.partner_id)
                cur = sale_line.order_id.pricelist_id.currency_id
                move.price_subtotal = cur.round(taxes['total'])
                move.order_price_unit = price_disc_unit
                move.margin = move.price_subtotal - move.cost_subtotal
                if move.price_subtotal > 0:
                    move.percent_margin = \
                        (move.margin / move.price_subtotal) * 100
                else:
                    move.percent_margin = 0
        _logger.debug("CMNT _get_subtotal %s", time.time() - init_t)