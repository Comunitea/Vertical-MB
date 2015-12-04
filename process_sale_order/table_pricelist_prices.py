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
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import api


class table_pricelist_prices(osv.Model):
    _name = "table.pricelist.prices"
    _rec_name = 'pricelist_id'
    _columns = {
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
                                        readonly=True,),
        'product_id': fields.many2one('product.product', 'Product',
                                      readonly=True, required=True),
        'price': fields.float('Price',
                              digits_compute=
                              dp.get_precision('Product Price'),
                              readonly=True,),
    }

    @api.one
    @api.model
    def recalculate_table(self):
        print "REACALCULA"
        self.ensure_one()
        t_product = self.env["product.product"]
        t_pricelist = self.env["product.pricelist"]
        domain = [('sale_ok', '=', True)]
        prod_objs = t_product.search(domain)
        domain = [('type', '=', 'sale')]
        pricelist_objs = t_pricelist.search(domain, order="id")
        for product in prod_objs:
            table = pricelist_objs.price_get_multi(products_by_qty_by_partner=
                                                   [(product, 1.0, False)])
            product_table = table[product.id]
            for pricelist in pricelist_objs:
                price = product_table[pricelist.id]
                if not price or price < -1 or price == 'warn':
                    price = 0.0
                domain = [
                    ('product_id', '=', product.id),
                    ('pricelist_id', '=', pricelist.id)
                ]
                rec_table = self.search(domain, limit=1)
                if not rec_table:
                    vals = {
                        'product_id': product.id,
                        'pricelist_id': pricelist.id,
                        'price': price
                    }
                    self.create(vals)
                else:
                    if price != rec_table.price:
                        rec_table.price = price
        return True

    # def recalculate_table(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     t_product = self.pool.get("product.product")
    #     t_pricelist = self.pool.get("product.pricelist")
    #     table_record_ids = self.search(cr, uid, [], context=context)
    #     self.unlink(cr, uid, table_record_ids, context=context)
    #     domain = [('sale_ok', '=', True)]
    #     product_ids = t_product.search(cr, uid, domain, context=context,
    #                                    order="id")
    #     domain = [('type', '=', 'sale')]
    #     pricelist_ids = t_pricelist.search(cr, uid, domain, context=context,
    #                                        order="id")
    #
    #     for product in t_product.browse(cr, uid, product_ids, context=context):
    #
    #         table = t_pricelist.price_get_multi(cr, uid, pricelist_ids,
    #                                             products_by_qty_by_partner=
    #                                             [(product, 1.0, False)])
    #         product_table = table[product.id]
    #         for pricelist_id in pricelist_ids:
    #             price = product_table[pricelist_id]
    #             if not price or price < -1 or price == 'warn':
    #                 price = 0.0
    #             vals = {
    #                 'product_id': product.id,
    #                 'pricelist_id': pricelist_id,
    #                 'price': price
    #             }
    #             self.create(cr, uid, vals, context=context)
    #     return True
