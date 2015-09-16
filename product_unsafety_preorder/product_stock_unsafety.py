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
from openerp.osv import osv
from openerp import api

class product_stock_unsafety(osv.Model):
    _inherit = 'product.stock.unsafety'

    def retry(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if ids:
            for cur in self.browse(cr, uid, ids):
                if cur.product_id.seller_ids:
                    seller = cur.product_id.seller_ids[0].name.id
                    self.write(cr,
                               uid,
                               cur.id,
                               {'supplier_id': seller,
                                'state': 'in_progress'})
        return True

    # def generate_preorder(self, cr, uid, ids, context=None):
    #     """
    #     Call the function that creates the pre-order.
    #     Supposing ids is unique because we call from a buttom
    #     We group by supplier and create a preorder with all products
    #     """
    #     if context is None:
    #         context = {}
    #     value = {}
    #     preorder = self.pool.get('purchase.preorder')
    #     for obj in self.browse(cr, uid, ids, context):  # One iteration
    #         if obj.supplier_id:
    #             vals = {'supplier_id': obj.supplier_id.id}
    #             preorder_id = preorder.create(cr, uid, vals, context=context)
    #             value = preorder.create_preorder(cr,
    #                                              uid,
    #                                              [preorder_id],
    #                                              obj.product_id.id,
    #                                              obj.minimum_proposal,
    #                                              context=context)
    #     return value

    @api.multi
    def generate_preorder(self):
        self.ensure_one()
        view = {}
        if self.supplier_id:
            domain = [
                ('supplier_id', '=', self.supplier_id.id),
                ('state', '=', 'in_progress')
            ]
            op_objs = self.search(domain)
            undermin_dic = {}
            for op in op_objs:
                undermin_dic[op.product_id.id] = op.minimum_proposal
            vals = {'supplier_id': self.supplier_id.id}
            preorder_obj = self.env['purchase.preorder'].create(vals)
            view = preorder_obj.\
                create_preorder(undermin_data=undermin_dic)
            op_objs.write({'preorder_id': preorder_obj.id,
                           'state': 'in_purchase'})
        return view
