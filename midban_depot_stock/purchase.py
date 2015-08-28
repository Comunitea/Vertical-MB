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
from openerp.osv import osv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import models, api


class purchase_order(osv.Model):
    _inherit = "purchase.order"

    def action_picking_create(self, cr, uid, ids, context=None):
        """
        Overwrite to add the current creation date instead of the defaults
        maX expected date of lines
        """
        for order in self.browse(cr, uid, ids):
            picking_vals = {
                'picking_type_id': order.picking_type_id.id,
                'partner_id': order.partner_id.id,
                # 'date': max([l.date_planned for l in order.order_line]),
                'date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'origin': order.name}
            picking_id = self.pool.get('stock.picking').create(cr, uid,
                                                               picking_vals,
                                                               context=context)
            self._create_stock_moves(cr, uid, order, order.order_line,
                                     picking_id, context=context)
    _defaults = {
        'invoice_method': 'picking'}


class purchase_order_line(osv.Model):
    _inherit = "purchase.order.line"

    def _get_date_planned(self, cr, uid, supplier_info, date_order_str,
                          context=None):
        """
        Overwrited.
        Returns the supplier delivery day closest to the default delivery date
        """
        supplier_delay = int(supplier_info.delay) if supplier_info else 0
        supp_res = datetime.strptime(date_order_str,
                                     DEFAULT_SERVER_DATETIME_FORMAT) +\
            relativedelta(days=supplier_delay)

        # If supplier days calc the closest to the default date_planned
        res = supp_res
        if supplier_info:
            s_days = [x.sequence for x in
                      supplier_info.name.supp_service_days_ids]
            week_day = supp_res.weekday() + 1  # bekause monday 0 sunday 6
            if s_days and week_day not in s_days:

                delta = 0
                while week_day not in s_days:
                    delta += 1
                    week_day = 1 if week_day == 7 else week_day + 1
                res = supp_res + timedelta(days=delta or 0.0)
        return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _prepare_order_line_move(self, order, order_line, picking_id,
                                 group_id):
        res = super(purchase_order, self)._prepare_order_line_move(order,
                                                                   order_line,
                                                                   picking_id,
                                                                   group_id)
        for dic in res:
            dic['product_uos_qty'] = order_line.product_uoc_qty
            dic['product_uos'] = order_line.product_uoc.id
        return res
