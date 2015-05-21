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


class sale_specific_price(models.Model):

    _name = 'sale.specific.price'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.one
    @api.depends('customer_id', 'product_id', 'sale_line_id', 'pricelist_id')
    def _get_pricelist_price(self):
        price = self.pricelist_id.price_get(self.product_id.product_variant_ids[0].id, 1.0, self.customer_id.id)
        self.pricelist_price = price[self.pricelist_id.id]

    @api.one
    @api.depends('pricelist_price', 'discount')
    def _get_specific_price(self):
        self.specific_price = self.pricelist_price * (1 - (self.discount/100))

    customer_id = fields.Many2one('res.partner', 'Customer', required=True)
    product_id = fields.Many2one('product.template', 'Produt', required=True)
    cost_price = fields.Float('Cost price')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', required=True)
    pricelist_price = fields.Float('Pricelist price', compute='_get_pricelist_price')
    specific_price = fields.Float('Specific price', compute='_get_specific_price')
    margin = fields.Float('Margin')
    start_date = fields.Date('Start date', required=True)
    end_date = fields.Date('End date', required=True)
    discount = fields.Float('Discount', required=True)
    sale_line_id = fields.Many2one('sale.order.line', 'Sale line id')
    state = fields.Selection(
        (('draft', 'Draft'), ('approved', 'Approved'),
         ('rejected', 'Rejected')), 'State', default='draft')

    @api.multi
    def act_approve(self):
        self.write({'state': 'approved'})
        return True

    @api.multi
    def act_reject(self):
        for price in self:
            if price.sale_line_id.invoice_lines:
                price.message_post(body=_("The sale is invoiced"))
            line = price.sale_line_id
            price.sale_line_id.discount = line.product_id.max_discount and \
                line.product_id.max_discount or \
                line.product_id.categ_id.max_discount

        self.write({'state': 'rejected'})
        return True
