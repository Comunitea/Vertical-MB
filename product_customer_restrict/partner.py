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
from openerp.osv import osv, fields
import time


class partner_rules(osv.Model):
    """Rules are used in order to know the catalog of products that
       can be sold to the customer."""
    _name = 'partner.rules'
    _description = 'Rules model associated to customer'
    _rec_name = 'partner_id'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer'),
        'start_date': fields.date('Start Date', required=True),
        'end_date': fields.date('End Date', required=True),
        'product_id': fields.many2one('product.product', 'Product'),
        'category_id': fields.many2one('product.category', 'Category'),
    }
    _defaults = {
        'start_date': lambda *a: time.strftime('%Y-01-01'),
        'end_date': lambda *a: time.strftime('%Y-12-31'),
    }

    def _check_repeated_product(self, cr, uid, ids, context=None):
        """Check rules of current  partner and his parents. If there are
           rules with the same product of current rule raises an error """
        part_pool = self.pool.get("res.partner")
        self_rule = self.browse(cr, uid, ids[0])
        if self_rule.product_id:
            partner_id = self_rule.partner_id.id
            check_ids = part_pool._get_parent_ids(cr, uid, partner_id)
            check_ids.append(partner_id)
            domain = [('partner_id', 'in', check_ids),
                      ('product_id', '=', self_rule.product_id.id),
                      ('id', '!=', self_rule.id)]
            rule_ids = self.search(cr, uid, domain)
            if rule_ids:
                return False
        return True

    def _check_repeated_category(self, cr, uid, ids, context=None):
        """Check rules of current  partner and his parents. If there are
           rules with the same product of current rule raises an error """
        part_pool = self.pool.get("res.partner")
        self_rule = self.browse(cr, uid, ids[0])
        if self_rule.category_id:
            partner_id = self_rule.partner_id.id
            check_ids = part_pool._get_parent_ids(cr, uid, partner_id)
            check_ids.append(partner_id)
            domain = [('partner_id', 'in', check_ids),
                      ('category_id', '=', self_rule.category_id.id),
                      ('id', '!=', self_rule.id)]
            rule_ids = self.search(cr, uid, domain)
            if rule_ids:
                return False
        return True

    def _check_empty_rules(self, cr, uid, ids, context=None):
        """Check rules of current  partner and his parents. If there are
           rules with the same product of current rule raises an error """
        self_rule = self.browse(cr, uid, ids[0])
        if not self_rule.category_id and not self_rule.product_id:
            return False
        return True

    _constraints = [(_check_empty_rules,
                     'Rules can not be empty. Please define a product or \
                      category.',
                    ['product_id', 'category_id']),
                    (_check_repeated_product,
                     'Product rule repeated.\nProduct is alredady defined in\
                     other rule, maybe in some parent customer rule',
                     ['product_id']),
                    (_check_repeated_category,
                     'Category repeated.\nCategory is alredady defined in this\
                     other rule, maybe in some parent customer rule',
                     ['category_id'])]


class res_partner(osv.Model):
    """ Adds restricted catalog to partners and a rules management system.
        Implements Nested set model with parent_left and parent_right in irder
        to get parent ids and child ids in easy way """
    _inherit = 'res.partner'
    _columns = {
        'rule_ids': fields.one2many('partner.rules', 'partner_id', 'Rules'),
        'exclusive_ids': fields.many2many('product.product',
                                          'exclusive_customer_rel',
                                          'partner_id',
                                          'product_id',
                                          'Exclusive products',
                                          ),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        'rule_type': fields.selection([
                                     ('specific_catalog',
                                      'Only Let this prosucts'),
                                     ('exclusive', 'Not let this products')],
            'Rule type', required=True),
    }
    _defaults = {
        'rule_type': 'specific_catalog'
    }
    _parent_store = True  # Active management of parent_left and parent_right
    _parent_name = "parent_id"

    def _check_rule_types(self, cr, uid, ids, context=None):
        """ Checks if there are different rule types defined in parent partners
            or child partners. Raises an error if this happen"""
        self_partner = self.browse(cr, uid, ids[0])
        check_ids = self._get_parent_ids(cr, uid, self_partner.id)
        check_ids.extend(self._get_child_ids(cr, uid, self_partner.id))
        if check_ids:
            domain = [('id', 'in', check_ids),
                      ('rule_type', '!=', self_partner.rule_type),
                      ('rule_ids', '!=', False)]
            partner_ids = self.search(cr, uid, domain)
            if partner_ids:
                return False
        return True

    _constraints = [(_check_rule_types,
                     'There are rules of different type defined in parent\
                     partners or child partners of this group',
                    ['rule_type'])]

    def _get_parent_ids(self, cr, uid, partner_id):
        """ Get parent ids of partner using the Nested set model,
            Return ids of parent parters"""
        res = []
        partner_pool = self.pool.get("res.partner")
        partner = self.browse(cr, uid, partner_id)
        if partner:
            domain = [('parent_left', '<', partner.parent_left),
                      ('parent_right', '>', partner.parent_right)]
            res = partner_pool.search(cr, uid, domain)
        return res

    def _get_child_ids(self, cr, uid, partner_id):
        """ Get child ids of a parent partner using the Nested set model.
            Returns ids of child partners"""
        res = []
        partner_pool = self.pool.get("res.partner")
        partner = self.browse(cr, uid, partner_id)
        if partner:
            domain = [('parent_left', '>', partner.parent_left),
                      ('parent_right', '<', partner.parent_right)]
            res = partner_pool.search(cr, uid, domain)
        return res

    def _remove_exclusives(self, cr, uid, cat_ids, check_ids, rtype):
        """ Remove ids of exclusive products on cat_ids if some product
            has a exclusive customer diferent of current customer and
            his parents."""
        if not cat_ids:
            check_ids = str(check_ids).replace('[', '(').replace(']', ')')
            sql = '''
                  select id from product_product
                  EXCEPT
                  select product_id from exclusive_customer_rel
                  where partner_id not in %s
                  ''' % (check_ids)
        else:
            check_ids = str(check_ids).replace('[', '(').replace(']', ')')
            cat_ids = str(cat_ids).replace('[', '(').replace(']', ')')
            cat_ids = str(cat_ids).replace('[', '(').replace(']', ')')
            if rtype == 'specific_catalog':
                sql = '''
                      select id from product_product where id in %s
                      EXCEPT
                      select product_id from exclusive_customer_rel
                      where partner_id not in  %s and product_id in %s
                      ''' % (cat_ids, check_ids, cat_ids)
            if rtype == 'exclusive':
                sql = '''
                      select id from product_product where id not in %s
                      EXCEPT
                      select product_id from exclusive_customer_rel
                      where partner_id not in %s
                      ''' % (cat_ids, check_ids)
        cr.execute(sql)
        res = cr.fetchall()
        res = [x[0] for x in res]
        return res

    def search_products_to_sell(self, cr, uid, partner_id, context={}):
        """ Returns ids of products that can be sold for the customer"""
        partner_pool = self.pool.get("res.partner")
        product_pool = self.pool.get("product.product")
        res, exclusive_ids, check_ids, catalog_ids = [], [], [], []
        check_ids = self._get_parent_ids(cr, uid, partner_id)
        check_ids.append(partner_id)  # In order to check child node too
        partner_ids = partner_pool.search(cr, uid, [('id', 'in', check_ids),
                                                    ('rule_ids', '!=', False)],
                                          context=context)
        rule_type = False
        if partner_ids:
            rule_type = self.browse(cr, uid, partner_ids[0]).rule_type
        for part in self.browse(cr, uid, check_ids):
            for rule in part.rule_ids:
                cur_date = time.strftime('%Y-%m-%d')
                if rule.start_date <= cur_date and cur_date <= rule.end_date:
                    if rule.category_id:
                        domain = [('categ_id.id', 'child_of',
                                  [rule.category_id.id])]
                        catalog_ids.extend(product_pool.search(cr, uid,
                                                               domain))
                    if rule.product_id:
                        catalog_ids.append(rule.product_id.id)
            exclusive_ids.extend([x.id for x in part.exclusive_ids])
        catalog_ids = list(set(catalog_ids))
        res = self._remove_exclusives(cr, uid, catalog_ids, check_ids,
                                      rule_type)
        if exclusive_ids:  # Add exclusive product of partner and his parents
            res.extend(exclusive_ids)
            res = list(set(res))
        return res
