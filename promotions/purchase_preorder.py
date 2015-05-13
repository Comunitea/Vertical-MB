# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class products_supplier(osv.Model):

    def _calculate_percentage_promo(self, cr, uid, ids, field_names, arg,
                                    context=None):
        res = {}
        for prod in self.browse(cr, uid, ids, context=context):
            res[prod.id] = 0.0
        return res

    def _have_promotion(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for prod in self.browse(cr, uid, ids, context=context):
            if prod.product_promotions:
                res[prod.id] = _('Has promotions')
            else:
                res[prod.id] = _("Don't has promotions")
        return res

    def _get_product_promotions(self, cr, uid, ids, field_name, args,
                                context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context):
            promos = []
            for promo in obj.preorder_id.supplier_id.promotion_ids:
                promo = promo.promotion_id
                if promo.applicable == u'purchase':
                    if promo.type == u'global':
                        promos.append(promo.id)
                    elif promo.type == u'product':
                        if promo.product.id == obj.product_id.id:
                            promos.append(promo.id)
                    elif promo.type == u'category':
                        if promo.product.category_id.id == \
                                obj.product_id.category_id.id:
                            promos.append(promo.id)
            res[obj.id] = promos
        return res

    _inherit = "products.supplier"
    _columns = {
        'precentage_promo': fields.function(_calculate_percentage_promo,
                                            type="float",
                                            string='percentage promo',
                                            readonly=True),
        'have_promotion': fields.function(_have_promotion,
                                          type="char",
                                          string='has promotion',
                                          readonly=True),
        'product_promotions':
            fields.function(_get_product_promotions, type='one2many',
                            relation="partner.promotion", string="Promotions",
                            readonly=True),
    }
