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
import time
import calendar


class product_template(osv.Model):
    _inherit = 'product.template'

    def _get_qty(self, cr, uid, ids, product_id, start, stop):
        """
        Query that returns the quantity consumed of a product
        between dates.
        """
        cr.execute("SELECT sum(s.product_qty) \
                    FROM stock_move s\
                    INNER JOIN stock_picking p on p.id=s.picking_id \
                    INNER JOIN stock_picking_type pt on p.picking_type_id=pt.id \
                    WHERE s.product_id=" + product_id +
                   " AND s.state='done' AND s.date>='" + start + "' \
                    AND s.date<='" + stop + "' \
                    AND pt.code='outgoing'")
        return cr.fetchall()

    def calc_remaining_days(self, cr, uid, ids, context=None):
        """ Returns the days left to go to the product for sale. It is
            based on the following algorithm:
            (stock Product / average sales per day)
        """
        product = self.browse(cr, uid, ids[0], context=context)
        # Declaration of variables and structures
        prev_year = 0.0
        prev_month = 0.0
        month_prev_year = 0.0
        avg_day = []
        sortedavg = []
        year = int(time.strftime('%Y')) - 1     # Previous year
        ayear = time.strftime('%Y')     # Actual year
        month = int(time.strftime('%m')) - 1    # Previous month
        if month == 0:
            month = 12
        amonth = time.strftime('%m')    # Actual month
        # First and last day of previous month
        first_day, last_day = calendar.monthrange(int(ayear), month)
        # First and last day of the current month in the previous year
        afirst_day, alast_day = calendar.monthrange(year, int(amonth))
        # Average daily sales in the previous year
        cdate_start = '01-01-' + str(year) + ' 00:00:01'
        cdate_stop = '31-12-' + str(year) + ' 23:59:59'
        prev_year = self._get_qty(cr,
                                  uid,
                                  ids,
                                  str(product.id),
                                  cdate_start,
                                  cdate_stop)
        if prev_year[0][0] is None:
            prev_year = 0.0
        else:
            if calendar.isleap(int(ayear)):
                prev_year = prev_year[0][0] / 366
            else:
                prev_year = prev_year[0][0] / 365
        avg_day.append(prev_year)
        # Average sales last month
        cdate_start = '01-' + str(month) + '-' + ayear + ' 00:00:01'
        date = str(last_day) + '-' + str(month) + '-' + ayear
        cdate_stop = date + ' 23:59:59'
        prev_month = self._get_qty(cr,
                                   uid,
                                   ids,
                                   str(product.id),
                                   cdate_start,
                                   cdate_stop)
        if prev_month[0][0] is None:
            prev_month = 0.0
        else:
            prev_month = prev_month[0][0] / last_day
        avg_day.append(prev_month)
        # Average sales for the same month last year
        cdate_start = '01-' + str(amonth) + '-' + str(year) + ' 00:00:01'
        date = str(alast_day) + '-' + str(amonth) + '-' + str(year)
        cdate_stop = date + ' 23:59:59'
        month_prev_year = self._get_qty(cr,
                                        uid,
                                        ids,
                                        str(product.id),
                                        cdate_start,
                                        cdate_stop)
        if month_prev_year[0][0] is None:
            month_prev_year = 0.0
        else:
            month_prev_year = month_prev_year[0][0] / alast_day
        avg_day.append(month_prev_year)
        # If the list contains the averages found is not empty,
        # the ordered high to low
        if avg_day:
            sortedavg = max(avg_day)

        return sortedavg

    def _calc_remaining_days(self, cr, uid, ids,
                             field_names, args, context=None):
        """ Returns the days left to go to the product for sale. It is
            based on the following algorithm:
            (stock Product / average sales per day)
        """
        res = {}
        days = 0.00
        for product in self.browse(cr, uid, ids, context=context):
            res1 = self.calc_remaining_days(cr, uid, [product.id], context)
            if res1 > 0:
                days = product.virtual_stock_conservative / res1
                if days <= 0.0:
                    res[product.id] = 0.0
                else:
                    res[product.id] = days
            else:
                res[product.id] = 0.0

        return res

    _columns = {
        'remaining_days_sale': fields.function(_calc_remaining_days,
                                               type='float',
                                               string='Remaining \
                                                       Days of Sale',
                                               readonly=True),
    }
