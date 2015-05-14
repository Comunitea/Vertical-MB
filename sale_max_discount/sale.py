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
from datetime import date, timedelta


class sale_order_line(models.Model):

    _inherit = 'sale.order.line'

    specific_price_id = fields.Many2one('sale.specific.price',
                                        'Specific price', copy=False)

    @api.multi
    @api.onchange('discount')
    def onchange_discount(self):
        res = {}
        for line in self:
            max_discount = line.product_id.max_discount and \
                line.product_id.max_discount or \
                line.product_id.categ_id.max_discount
            if max_discount and line.discount > max_discount:
                specific_price = self.env['sale.specific.price'].search(
                    [('product_id', '=', line.product_id.id),
                     ('customer_id', '=', line.order_id.partner_id.id),
                     ('specific_price', '<=',
                      line.price_unit * (1 - (line.discount/100))),
                     ('state', '=', 'approved'),
                     ('start_date', '<=', date.today()),
                     ('end_date', '>=', date.today())])
                if not specific_price:
                    res['warning'] = {'title': _('Warning!'),
                                      'message': _("""Discount is greather \
than the maximun discount of product. The sale need to be approved""")}
        return res

    @api.model
    def create(self, vals):
        line = super(sale_order_line, self).create(vals)
        max_discount = line.product_id.max_discount and \
            line.product_id.max_discount or \
            line.product_id.categ_id.max_discount
        specific_price = self.env['sale.specific.price'].search(
            [('product_id', '=', line.product_id.id),
             ('customer_id', '=', line.order_id.partner_id.id),
             ('specific_price', '<=', line.price_unit *
              (1 - (line.discount/100))),
             ('state', '=', 'approved'), ('start_date', '<=', date.today()),
             ('end_date', '>=', date.today())])
        if max_discount and line.discount > max_discount and not \
                specific_price:
            specific_vals = {
                'customer_id': line.order_id.partner_id.id,
                'product_id': line.product_id.id,
                'cost_price': line.product_id.standard_price,
                'pricelist_price': line.price_unit,
                'specific_price': line.price_unit * (1 - (line.discount/100)),
                'margin': line.product_id.margin,
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=30),
                'sale_line_id': line.id,
            }
            self.env['sale.specific.price'].create(specific_vals)
        return line

    @api.multi
    def write(self, vals):
        res = super(sale_order_line, self).write(vals)
        for line in self:
            if vals.get('discount', 0):
                max_discount = line.product_id.max_discount and \
                    line.product_id.max_discount or \
                    line.product_id.categ_id.max_discount
                _specific_price = self.env['sale.specific.price'].search(
                    [('product_id', '=', line.product_id.id),
                     ('customer_id', '=', line.order_id.partner_id.id),
                     ('specific_price', '<=',
                      line.price_unit * (1 - (line.discount/100))),
                     ('state', '=', 'approved'),
                     ('start_date', '<=', date.today()),
                     ('end_date', '>=', date.today())])
                if max_discount and line.discount > max_discount and not \
                        _specific_price:
                    specific_price = line.specific_price_id
                    if not specific_price:
                        specific_vals = {
                            'customer_id': line.order_id.partner_id.id,
                            'product_id': line.product_id.id,
                            'cost_price': line.product_id.standard_price,
                            'pricelist_price': line.price_unit,
                            'specific_price': line.price_unit *
                            (1 - (line.discount/100)),
                            'margin': line.product_id.margin,
                            'start_date': date.today(),
                            'end_date': date.today() + timedelta(days=30),
                            'sale_line_id': line.id,
                        }
                        self.env['sale.specific.price'].create(specific_vals)
                    else:
                        specific_price.write({
                            'customer_id': line.order_id.partner_id.id,
                            'product_id': line.product_id.id,
                            'cost_price': line.product_id.standard_price,
                            'pricelist_price': line.price_unit,
                            'specific_price': line.price_unit *
                            (1 - (line.discount/100)),
                            'margin': line.product_id.margin,
                        })
        return res
