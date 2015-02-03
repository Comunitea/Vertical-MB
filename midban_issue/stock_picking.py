# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Omar Castiñeira Saavedra$ <omar@pexego.es>
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


class stock_picking(osv.Model):

    _inherit = "stock.picking"

    def _get_purchase_id(self, cr, uid, ids, name, args, context=None):
        """
        Because of no procurement group in purchase order, search the related
        purchase order to incoming picking by name of the procurement group.
        This is made cause we need to know the purchase related in the
        default_get method of issue object.
        """
        # purchase_obj = self.pool.get("purchaseorder")
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            if picking.move_lines and picking.move_lines[0].purchase_line_id:
                res[picking.id] = picking.move_lines[0].purchase_line_id.\
                    order_id.id
        return res

    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        t_issue = self.pool.get('issue')
        return {
            picking_id: t_issue.search_count(cr, uid,
                                             [('res_model', '=',
                                              'stock.picking'),
                                              ('res_id', 'in', ids)],
                                             context=context)
            for picking_id in ids
        }

    def _search_purchase_id(self, cr, uid, obj, name, args, context=None):
        if context is None:
            context = {}
        t_purchase = self.pool.get('purchase.order')
        pick_ids = []
        for po in t_purchase.browse(cr, uid, args[0][2], context=context):
            pick_ids += [picking.id for picking in po.picking_ids
                         if picking.picking_type_code == 'incoming']
        res = [('id', 'in', pick_ids)]
        return res

    _columns = {
        'purchase_id': fields.function(_get_purchase_id, type="many2one",
                                       relation="purchase.order",
                                       string="Purchase Order",
                                       fnct_search=_search_purchase_id),
        'issue_count': fields.function(_issue_count, string='# Issues',
                                       type='integer'),
    }

    def issues_open(self, cr, uid, ids, context=None):
        """open issues related to pickings"""
        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference(cr, uid, 'midban_issue',
                                            'action_issue')
        action = self.pool.get(res[0]).read(cr, uid, res[1],
                                            context=context)
        action['domain'] = str([('res_model', '=', 'stock.picking'),
                                ('res_id', 'in', ids)])
        return action


# class stock_picking_in(osv.Model):

#     _inherit = "stock.picking.in"

#     def issues_open(self, cr, uid, ids, context=None):
#         pick_obj = self.pool.get('stock.picking')
#         return pick_obj.issues_open(cr, uid, ids, context=context)


# class stock_picking_out(osv.Model):

#     _inherit = "stock.picking.out"

#     def issues_open(self, cr, uid, ids, context=None):
#         pick_obj = self.pool.get('stock.picking')
#         return pick_obj.issues_open(cr, uid, ids, context=context)
