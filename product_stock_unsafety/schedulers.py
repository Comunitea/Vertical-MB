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
from openerp.tools.translate import _
import openerp


class procurement_order(osv.Model):
    _inherit = 'procurement.order'

    def _procure_orderpoint_confirm(self, cr, uid, use_new_cursor=False,
                                    company_id=False, context=None):
        '''
        Create procurement based on Orderpoint
        :param bool use_new_cursor: if set, use a dedicated cursor and
            auto-commit after processing each procurement.
            This is appropriate for batch jobs only.
        '''
        if context is None:
            context = {}
        if use_new_cursor:
            cr = openerp.registry(cr.dbname).cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        prod = self.pool.get('product.template')
        stock_unsafety = self.pool.get('product.stock.unsafety')
        dom = company_id and [('company_id', '=', company_id)] or []
        orderpoint_ids = orderpoint_obj.search(cr, uid, dom)
        prev_ids = []
        while orderpoint_ids:
            ids = orderpoint_ids[:100]
            del orderpoint_ids[:100]
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                virtual_stock = op.product_id.virtual_stock_conservative
                days_sale = op.product_id.remaining_days_sale
                # If the remaining days of product sales are less than the
                # minimum selling days configured in the rule of minimum stock
                # of the product. So instead of
                # creating another provision that would create a purchase, as
                # it would by default, creates a under minimum model.
                if (days_sale < op.min_days_id.days_sale) and \
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
                    daylysales = \
                        prod.calc_sale_units_per_day(cr, uid,
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
            if use_new_cursor:
                cr.commit()
            if prev_ids == ids:
                break
            else:
                prev_ids = ids

        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}
