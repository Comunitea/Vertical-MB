
# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Carlos Lombardía Rodríguez$ <carlos@comunitea.com>
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
from openerp.exceptions import except_orm
from openerp.tools.translate import _

class WizardOrderCategories(models.TransientModel):

    _name = 'wizard.order.categories'

    @api.model
    def default_get(self, fields):
        res = super( WizardOrderCategories, self).default_get(fields)
        list_product_order_vals = []
        active_ids = self.env.context.get('active_ids')
        if len(active_ids) > 1:
            raise Exception(u'Categories must be ordered individually')
        categ_id = active_ids[0]
        domain = [('categ_id', '=', categ_id),
                  ('state2', '=', 'registered')]
        prod_objs = self.env['product.template'].search(domain,
                                                        order="product_priority")
        for prod in prod_objs:
            vals = {
                'product_id': prod.id,
                'sequence': prod.product_priority,
                'wzd_id': self.id
            }
            list_product_order_vals.append((0,0, vals))
            product_order_obj = self.env['product.order'].create(vals)

        res.update({'product_order_ids': list_product_order_vals})
        return res

    product_order_ids = fields.One2many('product.order', 'wzd_id',
                                        "Products Order")

    @api.multi
    def set_defined_order(self):
        for wzd in self:
            for item in wzd.product_order_ids:
                item.product_id.product_priority = item.sequence
                sequence = str(item.product_id.categ_id.id).zfill(4) + \
                           str(item.sequence).zfill(4)
                item.product_id.sequence_order = sequence


        return

class ProductsOrder(models.TransientModel):

    _name = "product.order"

    wzd_id = fields.Many2one('wizard.order.categories', 'Wzd Order')

    product_id = fields.Many2one('product.template', 'Product',
                            readonly=True)
    sequence = fields.Integer('Order')
