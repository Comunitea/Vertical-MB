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
                     ('discount', '<=', line.discount),
                     ('state', '=', 'approved'),
                     ('pricelist_id', '=', line.order_id.pricelist_id.id),
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
             ('pricelist_id', '=', line.order_id.pricelist_id.id),
             ('discount', '<=', line.discount),
             ('state', '=', 'approved'), ('start_date', '<=', date.today()),
             ('end_date', '>=', date.today())])
        if max_discount and line.discount > max_discount and not \
                specific_price:
            specific_vals = {
                'customer_id': line.order_id.partner_id.id,
                'product_id': line.product_id.id,
                'cost_price': line.product_id.standard_price,
                'discount': line.discount,
                'pricelist_id': line.order_id.pricelist_id.id,
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
                     ('discount', '<=', line.discount),
                     ('pricelist_id', '=', line.order_id.pricelist_id.id),
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
                            'discount': line.discount,
                            'pricelist_id': line.order_id.pricelist_id.id,
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
                            'discount': line.discount,
                            'pricelist_id': line.order_id.pricelist_id,
                        })
        return res

    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product,
                                  qty=0, uom=False, qty_uos=0, uos=False,
                                  name='', partner_id=False, lang=False,
                                  update_tax=True,
                                  date_order=False,
                                  packaging=False,
                                  fiscal_position=False, flag=False,
                                  warehouse_id=False, context=None):
        sup = super(sale_order_line, self)
        res = sup.product_id_change_with_wh(cr, uid, ids, pricelist, product,
                                    qty=qty, uom=uom, qty_uos=qty_uos, uos=uos,
                                    name=name, partner_id=partner_id,
                                    lang=lang, update_tax=update_tax,
                                    date_order=date_order,
                                    packaging=packaging,
                                    fiscal_position=fiscal_position,
                                    warehouse_id=warehouse_id,
                                    flag=flag, context=context)
        if not product or not partner_id:
            return res
        specific_price = self.pool['sale.specific.price'].search(
            cr, uid,
            [('product_id', '=', product),
             ('customer_id', '=', partner_id),
             ('state', '=', 'approved'),
             ('start_date', '<=', date.today()),
             ('end_date', '>=', date.today())], context=context)
        print res['value']['discount']
        if specific_price:
            res['value']['discount'] = self.pool.get('sale.specific.price').\
                browse(cr, uid, specific_price, context).discount
        print res['value']['discount']
        return res

    @api.onchange('product_uos')
    def product_uos_onchange(self):
        super(sale_order_line, self).product_uos_onchange()
        if self.product_id and self.order_id.partner_id:
            specific_price = self.env['sale.specific.price'].search(
                [('product_id', '=', self.product_id.id),
                 ('customer_id', '=', self.order_id.partner_id.id),
                 ('state', '=', 'approved'),
                 ('start_date', '<=', date.today()),
                 ('end_date', '>=', date.today())])
            if specific_price:
                new_discount = specific_price[0].discount
                if new_discount > self.discount:
                    self.discount = new_discount
                    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='',
                          partner_id=False, lang=False, update_tax=True,
                          date_order=False, packaging=False,
                          fiscal_position=False, flag=False, context=None):
        sup = super(sale_order_line, self)
        res = sup.product_id_change(cr, uid, ids, pricelist, product,
                                    qty=qty, uom=uom, qty_uos=qty_uos, uos=uos,
                                    name=name, partner_id=partner_id,
                                    lang=lang, update_tax=update_tax,
                                    date_order=date_order,
                                    packaging=packaging,
                                    fiscal_position=fiscal_position,
                                    flag=flag, context=context)
        if not product or not partner_id:
            return res
        specific_price = self.pool['sale.specific.price'].search(
            cr, uid,
            [('product_id', '=', product),
             ('customer_id', '=', partner_id),
             ('state', '=', 'approved'),
             ('start_date', '<=', date.today()),
             ('end_date', '>=', date.today())], context=context)
        if specific_price:
            res['value']['discount'] = self.pool.get('sale.specific.price').browse(cr, uid, specific_price, context).discount
        return res
