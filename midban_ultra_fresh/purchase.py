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

    @api.model
    def default_get(self, fields):
        """
        Get a different picking.type.operation to manage ultrafresh purchases
        """
        res = super(purchase_order, self).default_get(fields)
        if res.get('ultrafresh_purchase', False):
            xml_name_id = 'midban_ultra_fresh.picking_type_ultrafresh'
            res['picking_type_id'] = self.env.ref(xml_name_id).id
        return res

    ultrafresh_purchase = fields.Boolean('Ultrafresh purchase', readonly=True)

    @api.model
    def _prepare_order_line_move(self, order, order_line, picking_id,
                                 group_id):
        res = super(purchase_order, self)._prepare_order_line_move(order,
                                                                   order_line,
                                                                   picking_id,
                                                                   group_id)
        for dic in res:
            dic['real_weight'] = order_line.purchased_kg
        return res


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
            qty = line.ultrafresh_po and line.purchased_kg or line.product_qty
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
