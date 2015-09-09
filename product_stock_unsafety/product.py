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
from openerp import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class product_template(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _get_qty(self, start, stop):
        """
        Query that returns the quantity consumed of a product
        between dates.
        """
        start_str = start.strftime('%Y-%m-%d') + ' 00:00:01'
        stop_str = stop.strftime('%Y-%m-%d') + ' 23:59:59'
        prod_ids = '(' + ', '.join(map(str, self.product_variant_ids._ids)) + \
            ')'
        self.env.cr.execute("SELECT sum(s.product_qty) \
                             INNER JOIN stock_picking p on p.id=s.picking_id \
                             INNER JOIN stock_picking_type pt \
                                on p.picking_type_id=pt.id \
                            WHERE s.product_id in " + prod_ids +
                            " AND s.state='done' AND \
                            s.date>='" + start_str + "' AND s.date<='"
                            + stop_str + "' AND pt.code='outgoing'")
        return self.env.cr.fetchall()

    @api.multi
    def calc_remaining_days(self):
        # period_last_year = self.env['ir.config_parameter'].search(
        #     [('key', '=', 'configured.period.last.year')])
        # period_adjustement = self.env['ir.config_parameter'].search(
        #     [('key', '=', 'configured.period.adjustement')])
        # if not period_last_year or not period_adjustement:
        #     return 0.0
        # period_last_year = int(period_last_year.value)
        # period_adjustement = int(period_adjustement.value)
        # # Se calculan las ventas del periodo:
        # # desde hoy hasta hoy + dias_configurados del año anterior.
        # init_last_year = date.today() + relativedelta(years=-1)
        # end_last_year = date.today() + relativedelta(days=period_last_year) + \
        #     relativedelta(years=-1)
        # qty_last_year = self._get_qty(init_last_year, end_last_year)
        # if qty_last_year[0][0] is None:
        #     qty_last_year = 0.0
        # else:
        #     qty_last_year = qty_last_year[0][0] / period_last_year
        #
        # # Se calcula el factor de correccion con las ventas en el periodo
        # # configurado. ventas desde hoy-dias_configurados hasta hoy
        # # y del mismo periodo del año anterior
        # init_adjust_curyear = date.today() + \
        #     relativedelta(days=-period_adjustement)
        # end_adjust_curyear = date.today()
        # qty_adjust_curyear = self._get_qty(init_adjust_curyear,
        #                                    end_adjust_curyear)
        # if qty_adjust_curyear[0][0] is None:
        #     qty_adjust_curyear = 0.0
        # else:
        #     qty_adjust_curyear = qty_adjust_curyear[0][0]
        #
        # init_adjust_lastyear = date.today() + \
        #     relativedelta(days=-period_adjustement) + relativedelta(years=-1)
        # end_adjust_lastyear = date.today() + relativedelta(years=-1)
        # qty_adjust_lastyear = self._get_qty(init_adjust_lastyear,
        #                                     end_adjust_lastyear)
        # if qty_adjust_lastyear[0][0] is None:
        #     qty_adjust_lastyear = 0.0
        # else:
        #     qty_adjust_lastyear = qty_adjust_lastyear[0][0]
        #
        # correction = (qty_adjust_lastyear / 100.0 * (qty_adjust_curyear -
        #                                              qty_adjust_lastyear)) / \
        #     100.0
        # final_daily_sale = qty_last_year * (1 + correction)
        final_daily_sale = 0
        return final_daily_sale

    @api.one
    @api.depends('virtual_stock_conservative')
    def _calc_remaining_days(self):
        days = 0.00
        res1 = self.calc_remaining_days()
        if res1 > 0:
            days = round(self.virtual_stock_conservative / res1)
            if days <= 0.0:
                self.remaining_days_sale = 0.0
            else:
                self.remaining_days_sale = days
        else:
            self.remaining_days_sale = 0.0

    remaining_days_sale = fields.Float('Remaining days of sale', readonly=True,
                                       compute='_calc_remaining_days')
