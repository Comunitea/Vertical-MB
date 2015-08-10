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
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round
from openerp.exceptions import except_orm


class product_template(models.Model):
    """
    Adding field minimum unit of sale, and box prices, this fields are Only
    shown in product.product view (Product variants) in order to avoid conflict
    betwen onchanges because of fields list_price of product.template and
    lst_price of product.producr models.
    """
    _inherit = "product.template"

    box_discount = fields.Float('Box Unit Discount',
                                help="When you sale this product in boxes"
                                "This will be the % discounted over the price"
                                "unit. If a box have 10 units and discount is"
                                "20%, the new box price will be 80 intead of"
                                "100, imaging price unit equals to 1.")




class ProductUom(models.Model):

    _inherit = 'product.uom'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only allowed products for a product
            if product_id is in context."""
        if context is None:
            context = {}
        if context.get('product_id', False):
            t_prod = self.pool.get('product.product')
            prod = t_prod.browse(cr, uid, context['product_id'], context)
            product_udv_ids = prod.get_sale_unit_ids()
            # Because sometimes args = [category = False]
            args = [['id', 'in', product_udv_ids]]
        return super(ProductUom, self).search(cr, uid, args,
                                              offset=offset,
                                              limit=limit,
                                              order=order,
                                              context=context,
                                              count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        res = super(ProductUom, self).name_search(name, args=args,
                                                  operator=operator,
                                                  limit=limit)
        if self._context.get('product_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            res = recs.name_get()
        return res
