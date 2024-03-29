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
from openerp import api


class procurement_order(osv.Model):
    _inherit = 'procurement.order'

    @api.multi
    def update_under_minimum(self, vals):
        """
        First check if already exists under_minimum in purchase state. If
        exists we do nothing. If not exist we check if exist under_minimum
        in progress state, if that case we update it else we create a new one
        """

        stock_unsafety = self.env['product.stock.unsafety']
        domain = [
            ('state', '=', 'in_purchase'),
            ('product_id', '=', vals['product_id'])
        ]
        under_mins = stock_unsafety.search(domain)
        if not under_mins:
            domain = [
                ('state', '=', 'in_progress'),
                ('product_id', '=', vals['product_id'])
            ]
            under_mins = stock_unsafety.search(domain)
            if under_mins:
                under_mins.write(vals)
            else:
                stock_unsafety.create(vals)
        return

    def _procure_orderpoint_confirm(self, cr, uid, use_new_cursor=False,
                                    company_id=False, context=None):
        '''
        Create procurement based on Orderpoint
        :param bool use_new_cursor: if set, use a dedicated cursor and
            auto-commit after processing each procurement.
            This is appropriate for batch jobs only.
         If the remaining days of product sales are less than the
         minimum selling days configured in the rule of minimum stock
         of the product. So instead of creating another provision that would
         create a purchase, ast would by default,
         creates a under minimum model.
        '''
        if context is None:
            context = {}
        if use_new_cursor:
            cr = openerp.registry(cr.dbname).cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        prod_tmp_obj = self.pool.get('product.template')

        dom = company_id and [('company_id', '=', company_id)] or []
        orderpoint_ids = orderpoint_obj.search(cr, uid, dom)
        prev_ids = []
        while orderpoint_ids:
            ids = orderpoint_ids[:100]
            del orderpoint_ids[:100]
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                prod = op.product_id
                if prod.seller_ids:
                    seller = prod.seller_ids[0]
                    state = 'in_progress'
                else:
                    state = 'exception'
                    seller = False
                days_sale = prod.remaining_days_sale
                min_days_sale = op.min_days_id.days_sale
                delay = seller and seller.delay or 0
                # Obtener dias max entre dos días de servicio
                max_dist_order = seller and seller.name.max_distance or 0
                real_minimum = min_days_sale + delay + max_dist_order
                if (days_sale < real_minimum) and prod.active:
                    vals = {'product_id': prod.id,
                            'name': _('Minimum Stock Days'),
                            'supplier_id': seller.name.id,
                            'orderpoint_id': op.id,
                            'responsible': uid,
                            'state': state}
                    prod_tmpl_id = prod.product_tmpl_id.id
                    daylysales = \
                        prod_tmp_obj.calc_sale_units_per_day(cr, uid,
                                                             [prod_tmpl_id],
                                                             context=context)
                    remaining_days = real_minimum - days_sale
                    if daylysales and remaining_days:
                        vals['minimum_proposal'] = daylysales * remaining_days

                    # Creating or updating existing under minimum
                    self.update_under_minimum(cr, uid, ids, vals,
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
