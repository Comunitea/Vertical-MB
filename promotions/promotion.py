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


class partner_promotion(osv.Model):
    _name = "partner.promotion"
    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'type': fields.selection([('product', 'Product'),
                                 ('category', 'Category'),
                                 ('global', 'Global')], 'Type', required=True),
        'product': fields.many2one('product.product', 'Product'),
        'category': fields.many2one('product.category', 'Category'),
        'discount': fields.float('Discount'),
        'init_date': fields.date('Initial date', required=True),
        'final_date': fields.date('Final date'),
        'accumulated': fields.boolean('Accumulated'),
        'applicable': fields.selection([('sale', 'Sale'),
                                        ('purchase', 'Purchase')],
                                       'Applicable', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),

    }

    _defaults = {
        'type': 'global',
    }

    def _get_invoice_discounts(self, cr, uid, product_id, partner_id,
                               date, type, context):
        ir_model_data_obj = self.pool.get('ir.model.data')
        mdid = ir_model_data_obj.get_object_reference(cr, uid,
                                                      'promotions',
                                                      'discount_type_promotions')
        if mdid:
            mdid = mdid[1]
        else:
            raise osv.except_osv(_('Not found register'),
                                 _('Not found promotion discount type'))
        promo_obj = self.pool.get('partner.promotion.rel')
        context = dict(context)
        context.update({'type_promo': 'purchase',
                        'domain_promotion': type})
        applieds = promo_obj.get_applied_promos(cr, uid, product_id,
                                                partner_id, date, context)
        discounts = []
        for applied in promo_obj.browse(cr, uid, applieds['accumulated'],
                                        context):
            discounts.append((0, 0, {
                'mode': 'A',
                'type_id': mdid,
                'percentage': applied.promotion_id.discount,
                'sequence': 1,
            }))
        for applied in promo_obj.browse(cr, uid, applieds['sequence'],
                                        context):
            discounts.append((0, 0, {
                'mode': 'A',
                'type_id': mdid,
                'percentage': applied.promotion_id.discount,
                'sequence': applied.sequence,
            }))
        return discounts
