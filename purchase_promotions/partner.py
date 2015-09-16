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


class partner_promotion_rel(osv.Model):
    _name = 'partner.promotion.rel'
    _description = 'Partner promotion table rel'
    _columns = {
        'sequence': fields.integer('Sequence', required=False),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'promotion_id': fields.many2one('partner.promotion', 'Promotion',
                                        required=True),
        'accumulated': fields.related('promotion_id', 'accumulated',
                                      type='boolean', string='Accumulated',
                                      readonly=True)
    }

    _defaults = {
        'sequence': 1,
    }

    def onchange_promotion_id(self, cr, uid, ids, promotion_id=None,
                              context=None):
        vals = {}
        if promotion_id:
            promo = self.pool.get('partner.promotion').browse(cr, uid,
                                                              promotion_id,
                                                              context)
            vals['accumulated'] = promo.accumulated
            return {'value': vals}
        return {}

    def _in_date(self, cr, uid, date, promo, context={}):
        if date >= promo.init_date:
            if promo.final_date:
                if date <= promo.final_date:
                    return True
            else:
                return True
        return False

    def get_applied_promos(self, cr, uid, prod_id, partner_id, date,
                           context={}):
        type_promo = context.get('type_promo', 'purchase')
        dom_promo = context.get('domain_promotion', 'all')
        applied = {'accumulated': [], 'sequence': []}
        for type in applied.keys():
            accumulated = type == 'accumulated' and True or False
            promo_ids = self.search(cr, uid, [('partner_id', '=', partner_id),
                                              ('accumulated', '=',
                                               accumulated)],
                                    context=context)
            applied_promos = []
            for promo in self.browse(cr, uid, promo_ids, context):
                if promo.promotion_id.applicable != type_promo:
                    continue
                if promo.promotion_id.type == 'global' and \
                        dom_promo in ('global', 'all'):
                    if self._in_date(cr, uid, date, promo.promotion_id):
                        applied_promos.append(promo.id)
                    continue
                if not promo.promotion_id.type == 'category' and \
                        not promo.promotion_id.type == 'product':
                    continue
                if prod_id and dom_promo in ('line', 'all'):
                    product = self.pool.get('product.product').browse(cr, uid,
                                                                      prod_id,
                                                                      context)
                    if promo.promotion_id.type == 'category':
                        if promo.promotion_id.category.id == \
                                product.categ_id.id and \
                                self._in_date(cr, uid, date,
                                              promo.promotion_id):
                            applied_promos.append(promo.id)
                    else:
                        if promo.promotion_id.product.id == product.id and \
                                self._in_date(cr, uid, date,
                                              promo.promotion_id):
                            applied_promos.append(promo.id)
            applieds_ordered = self.search(cr, uid, [('id', 'in',
                                                      applied_promos)],
                                           order='sequence',
                                           context=context)
            applied[type] = applieds_ordered
        return applied


class res_partner(osv.Model):
    _inherit = "res.partner"
    _columns = {
        'promotion_ids': fields.one2many('partner.promotion.rel', 'partner_id',
                                         'Promotions'),
    }
