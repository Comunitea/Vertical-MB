# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios TEcnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra$ <omar@comunitea.com>
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
        promo_obj = self.pool.get('partner.promotion.rel')
        ctx = dict(context)
        ctx.update({'type_promo': 'purchase',
                    'domain_promotion': 'all'})
        for obj in self.browse(cr, uid, ids, context=context):
            price_disc = 100.0
            applieds = promo_obj.get_applied_promos(cr, uid,
                                                    obj.product_id.id or
                                                    False,
                                                    obj.preorder_id.
                                                    supplier_id.id,
                                                    fields.date.today(), ctx)
            discount = 0.0
            for applied in promo_obj.browse(cr, uid, applieds['accumulated'],
                                            ctx):
                discount += price_disc * (applied.promotion_id.discount /
                                          100.0)
            price_disc -= discount
            for applied in promo_obj.browse(cr, uid, applieds['sequence'],
                                            ctx):
                price_disc -= price_disc * (applied.promotion_id.discount /
                                            100.0)
            if price_disc != 100.0:
                res[obj.id] = 100.0 - ((price_disc * 100.0) / 100.0)
            else:
                res[obj.id] = 0.0
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
                if promo.applicable == u'purchase' and \
                        (not promo.final_date
                         or promo.final_date < fields.date.today()):
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
        'product_promotions': fields.
        function(_get_product_promotions, type='one2many',
                 relation="partner.promotion", string="Promotions",
                 readonly=True),
    }
