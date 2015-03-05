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
from openerp import pooler
from openerp.tools.translate import _


class procurement_order(osv.Model):
    _inherit = 'procurement.order'

    def _procure_orderpoint_confirm(self, cr, uid, automatic=False,
                                    use_new_cursor=False, context=None,
                                    user_id=False):
        '''
        Create Under Minimums based on Orderpoint
        use_new_cursor: False or the dbname

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param user_id: The current user ID for security checks
        @param context: A standard dictionary for contextual values
        @param param: False or the dbname
        @return:  Dictionary of values
        """
        '''
        if context is None:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        stock_unsafety = self.pool.get('product.stock.unsafety')
        prod = self.pool.get('product.product')
        offset = 0
        ids = [1]
        seller = False
        if automatic:
            self.create_automatic_op(cr, uid, context=context)
        while ids:
            ids = orderpoint_obj.search(cr, uid, [], offset=offset, limit=100)
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                virtual_stock = op.product_id.virtual_stock_conservative
                days_sale = op.product_id.remaining_days_sale
                # If the remaining days of product sales are less than the
                # minimum selling days configured in the rule of minimum stock
                # of the product or the virtual stock conservative product is
                # less than the minimum amount you have configured the rule of
                # minimum stock of the product; break the stock. So instead of
                # creating another provision that would create a purchase, as
                # it would by default, creates a low minimum.
                if (days_sale < op.min_days_id.days_sale or
                   virtual_stock < op.product_min_qty) and \
                   op.product_id.active:
                    if op.product_id.seller_ids:
                        seller = op.product_id.seller_ids[0].name.id
                        state = 'in_progress'
                    else:
                        state = 'exception'
                    vals = {'product_id': op.product_id.id,
                            'supplier_id': seller,
                            'min_fixed': op.product_min_qty,
                            'real_stock': op.product_id.qty_available,
                            'virtual_stock': virtual_stock,
                            'responsible': uid,
                            'state': state}
                    daylysales = prod.calc_remaining_days(cr,
                                                          uid,
                                                          [op.product_id.id],
                                                          context=context)
                    if daylysales and op.min_days_id.days_sale:
                        vals['minimum_proposal'] = daylysales * \
                            op.min_days_id.days_sale
                    if days_sale < op.min_days_id.days_sale:
                        vals['name'] = _('Days sale')
                    if virtual_stock < op.product_min_qty:
                        vals['name'] = _('Minimum Stock')
                    stock_unsafety.create(cr,
                                          uid,
                                          vals,
                                          context=context)
            offset += len(ids)
            if use_new_cursor:
                cr.commit()
        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}
