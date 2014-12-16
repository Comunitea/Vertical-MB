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
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    ultrafresh_purchase = fields.Boolean('Ultrafresh purchase', readonly=True)


class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _amount_line(self):
    	"""
    	Need call super???
    	"""
    	# import ipdb; ipdb.set_trace()
    	# res = super(purchase_order_line, self)._amount_line(prop, arg)
    	for line in self:
			qty =  line.ultrafresh_po and line.purchased_kg or line.product_qty
			price = line.price_unit
			taxes = line.taxes_id.compute_all(price, qty, line.product_id,
				                              line.order_id.partner_id)
			cur = line.order_id.pricelist_id.currency_id
			line.price_subtotal = cur.round(taxes['total'])

    purchased_kg = fields.Float('Purchased Kg')
    ultrafresh_po = fields.Boolean('Ultrafresh purchase', readonly=True,
    	                           related='order_id.ultrafresh_purchase')
    price_subtotal = fields.Float('Subtotal', compute=_amount_line,
                                  required=True, readonly=True,
                                  digits_compute=
                                  dp.get_precision('Account'))
    # @api.model
    # def _amount_line(self):
    #     """
    #     When we sale in boxes we want to do product_uos_qty * price unit
    #     instead the default product_uom_qty * price_unit
    #     """
    #     for rec in self:
    #         if rec.choose_unit == 'box':  # product_uos_qty instead uom
    #             unit_of_measure_qty = rec.product_uos_qty
    #         else:  # choose_unit == unit
    #             unit_of_measure_qty = rec.product_uom_qty
    #         price = rec.price_unit * (1 - (rec.discount or 0.0) / 100.0)
    #         taxes = rec.tax_id.compute_all(price, unit_of_measure_qty,
    #                                        rec.product_id,
    #                                        rec.order_id.partner_id)
    #         cur = rec.order_id.pricelist_id.currency_id
    #         rec.price_subtotal = cur.round(taxes['total'])


    
    			
