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


class product_template(osv.Model):
    """ """
    _inherit = 'product.template'
    _columns = {
        'exclusive_ids': fields.many2many('res.partner',
                                          'exclusive_customer_rel',
                                          'product_id',
                                          'partner_id',
                                          'Exclusive customers',
                                          domain=[('customer', '=', True)]),
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only allowed products for a partner
            if partner_id is in context."""
        if context is None:
            context = {}
        part_pool = self.pool.get("res.partner")
        if context.get('partner_id', False):  # Search only allowed products
            part_id = context['partner_id']
            if context.get('no_rule', False):  # No rules,avoid exclusives
                check_ids = part_pool._get_parent_ids(cr, uid, part_id)
                check_ids.append(part_id)
                list_ids = part_pool._remove_exclusives(cr, uid, [], check_ids,
                                                        False)
                exclusive_ids = []  # Add exclusives of partner and parents
                for part in part_pool.browse(cr, uid, check_ids):
                    exclusive_ids.extend([x.id for x in part.exclusive_ids])
                list_ids.extend(exclusive_ids)
                list_ids = list(set(list_ids))
            else:  # Evaluate rules and exclusives
                list_ids = part_pool.search_products_to_sell(cr, uid, part_id)
                args.append(['id', 'in', list_ids])
        return super(product_template, self).search(cr, uid, args,
                                                    offset=offset,
                                                    limit=limit,
                                                    order=order,
                                                    context=context,
                                                    count=count)

    def _get_partner_buyer(self, cr, uid, ids, context=None):
        """ Return ids of partners that can buy the product"""
        res = []
        part_pool = self.pool.get("res.partner")
        product = self.browse(cr, uid, ids[0])
        if product.exclusive_ids:
            res = [x.id for x in product.exclusive_ids]
            for partner_id in res:
                childs = part_pool._get_child_ids(cr, uid, partner_id)
                res.extend(childs)
        else:
            partner_ids = part_pool.search(cr, uid, [])
            for part in part_pool.browse(cr, uid, partner_ids):
                partner_products = part_pool.search_products_to_sell(cr, uid,
                                                                     part.id)
                if product.id in partner_products:
                    res.append(part.id)
        return res

    def view_partner_buyer(self, cr, uid, ids, context=None):
        """Returns a customer view of partners that can buy the product"""
        if context is None:
            context = {}
        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference(cr, uid, 'base',
                                            'action_partner_form')
        action = self.pool.get(res[0]).read(cr, uid, res[1],
                                            context=context)

        list_ids = self._get_partner_buyer(cr, uid, ids, context=context)
        domain = str([('id', 'in', list_ids)])
        action['domain'] = domain

        return action


class product_product(osv.Model):
    _inherit = 'product.product'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only allowed products for a partner
            if partner_id is in context."""
        if context is None:
            context = {}
        part_pool = self.pool.get("res.partner")
        if context.get('partner_id', False):  # Search only allowed products
            part_id = context['partner_id']
            if context.get('no_rule', False):  # No rules,avoid exclusives
                check_ids = part_pool._get_parent_ids(cr, uid, part_id)
                check_ids.append(part_id)
                list_ids = part_pool._remove_exclusives(cr, uid, [], check_ids,
                                                        False)
                exclusive_ids = []  # Add exclusives of partner and parents
                for part in part_pool.browse(cr, uid, check_ids):
                    exclusive_ids.extend([x.id for x in part.exclusive_ids])
                list_ids.extend(exclusive_ids)
                list_ids = list(set(list_ids))
            else:  # Evaluate rules and exclusives
                list_ids = part_pool.search_products_to_sell(cr, uid, part_id)
                args.append(['id', 'in', list_ids])
        return super(product_product, self).search(cr, uid, args,
                                                   offset=offset,
                                                   limit=limit,
                                                   order=order,
                                                   context=context,
                                                   count=count)
