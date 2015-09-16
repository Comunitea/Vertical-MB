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
from datetime import date
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
        self.env.cr.\
            execute("SELECT sum(sm.product_qty) \
                     FROM stock_move sm \
                     INNER JOIN stock_picking p on p.id=sm.picking_id \
                     INNER JOIN stock_picking_type pt \
                     on p.picking_type_id=pt.id \
                    WHERE sm.product_id in " + prod_ids +
                    " AND sm.state='done' AND \
                      sm.date >= '" + start_str + "' AND sm.date<='"
                    + stop_str + "' AND pt.code='outgoing'")
        return self.env.cr.fetchall()[0][0]

    def _get_product_periods(self):
        """
        Get the consult period and the adjustement period first from product
        and then from configuration parametres
        """
        last_year = adjustement = 0
        if self.specific_periods:
            last_year = self.specific_consult_period
        else:
            domain = [('key', '=', 'configured.consult.period')]
            consult_period = self.env['ir.config_parameter'].search(domain)
            last_year = int(consult_period.value)

        if self.specific_periods:
            adjustement = self.specific_adjustement_period
        else:
            domain = [('key', '=', 'configured.adjustement.period')]
            adjustement_period = self.env['ir.config_parameter'].search(domain)
            adjustement = int(adjustement_period.value)
        return last_year, adjustement

    @api.multi
    def calc_sale_units_per_day(self):
        # Get periods from product or from configuration parametres
        consult_period, adjustement_period = self._get_product_periods()
        if not consult_period:
            return 0.0
        # Se calculan las ventas del periodo:
        # desde hoy hasta hoy + dias_configurados del año anterior.
        init_last_year = date.today() + relativedelta(years=-1)
        end_last_year = date.today() + relativedelta(days=consult_period) + \
            relativedelta(years=-1)
        sale_qty = self._get_qty(init_last_year, end_last_year)
        if sale_qty is None or not sale_qty:
            # Calculo la cantidad en este año en lugar del anterior
            init_current_year = date.today() + \
                relativedelta(days=-consult_period)
            end_current_year = date.today()
            sale_qty = self._get_qty(init_current_year, end_current_year)
            if sale_qty is None or not sale_qty:
                return 0.0

        # Se calcula el factor de correccion con las ventas en el periodo
        # configurado. ventas desde hoy-dias_configurados hasta hoy
        init_adjust_curyear = date.today() + \
            relativedelta(days=-adjustement_period)
        end_adjust_curyear = date.today()
        sale_qty_adjust_curyear = self._get_qty(init_adjust_curyear,
                                                end_adjust_curyear)
        if sale_qty_adjust_curyear is None:
            sale_qty_adjust_curyear = 0.0

        # Lo mismo para el año anterior
        init_adjust_lastyear = date.today() + \
            relativedelta(days=-adjustement_period) + relativedelta(years=-1)
        end_adjust_lastyear = date.today() + relativedelta(years=-1)
        sale_qty_adjust_lastyear = self._get_qty(init_adjust_lastyear,
                                                 end_adjust_lastyear)
        if sale_qty_adjust_lastyear is None:
            sale_qty_adjust_lastyear = 0.0

        # Calc of stock_per_day
        diff_sales = sale_qty_adjust_curyear - sale_qty_adjust_lastyear
        corr_fact = 0
        if sale_qty_adjust_lastyear:
            corr_fact = diff_sales / sale_qty_adjust_lastyear
        sale_qty_per_day = sale_qty / consult_period
        stock_per_day = sale_qty_per_day + \
            (sale_qty_per_day * corr_fact)
        return stock_per_day

    @api.one
    @api.depends('virtual_available')
    def _calc_remaining_days(self):
        stock_days = 0.00
        if self.virtual_available:
            stock_days = -1.00  # Indicates we dont know stock days
            stock_per_day = self.calc_sale_units_per_day()
            if stock_per_day > 0:
                stock_days = round(self.virtual_available /
                                   stock_per_day)

        self.remaining_days_sale = stock_days

    remaining_days_sale = fields.Float('Remaining Stock Days', readonly=True,
                                       compute='_calc_remaining_days',
                                       help=" Stock measure in days of sale "
                                       "calculed consulting configured "
                                       "periods")
    specific_periods = \
        fields.Boolean('Specific Periods',
                       help='If checked we can specify the periods to '
                       'calculate the remaining stock days else we use the '
                       'general configuration of consult and ajust periods')
    specific_consult_period = \
        fields.Integer('Consult Period Stock Days',
                       help='Used to calculate remaining stock days. '
                       'It will check from today '
                       'to X period days of the last year the quantity sold. '
                       'if not sales in last year we check the period going '
                       'back this days since today')
    specific_adjustement_period = \
        fields.Integer('Adjustement Period Stock Days',
                       help='Used to calculate remaining stock days. '
                       'It will check a period from '
                       'today back to this days, of the last and the '
                       'current year to get the diferent trend in sales')
