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

# from openerp import tools
# from openerp.osv import fields, osv
from openerp import models, fields, tools


class route_report(models.Model):
    _name = "route.report"
    _description = "Route analysis view"
    _auto = False
    _rec_name = 'date'
    # _order = 'sequence'

    customer_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    result = fields.Selection([('sale_done', 'Sale done'),
                               ('visited_no_order', 'Visited without order'),
                               ('closed_day', 'Closed day'),
                               ('closed_holidays', 'Holidays'),
                               ('closed_reform', 'Closed Reform'),
                               ('no_visited', 'No visited'),
                               ('delivered_ok', 'Delivered OK'),
                               ('delivered_issue', 'Delivered with issue'),
                               ('not_responding', 'Not responding'),
                               ('comunicate', 'Comunicate'),
                               ('call_no_order', 'Call without order'),
                               ('call_other_day', 'Call other day'),
                               ('call_no_done', 'Call not done')],
                              string="result", readonly=True)
    route_id = fields.Many2one('route', 'Route', readonly=True)
    date = fields.Date('Date', readonly=True)
    detail_state = fields.Selection([('pending', 'Pending'),
                                     ('on_course', 'On course'),
                                     ('cancelled', 'Cancelled'),
                                     ('closed', 'Closed')],
                                    string="Detail State",
                                    readonly=True)
    comercial_id = fields.Many2one('res.users', 'Comercial')
    route_type = fields.Selection([('auto_sale', 'Auto Sale'),
                                   ('comercial', 'Comercial'),
                                   ('delivery', 'Delivery'),
                                   ('telesale', 'Telesale'),
                                   ('ways', 'Ways'),
                                   ('other', 'Other')], 'Rouet Type',
                                  readonly=True)
    route_day_id = fields.Many2one('week.days', 'Week day', readonly=True)
    route_state = fields.Selection([('draft', 'Draft'), ('active', 'Active')],
                                   string="Route State",
                                   readonly=True)
    count_visits = fields.Integer('Nº Visits', readonly=True)

    def _select(self):
        select_str = """
            SELECT min(CL.id) as id,
                   CL.customer_id as customer_id,
                   CL.result as result,
                   RD.route_id as route_id,
                   RD.date as date,
                   RD.state as detail_state,
                   RD.comercial_id as comercial_id,
                   R.type as route_type,
                   R.day_id as route_day_id,
                   R.state as route_state,
                   1 as count_visits
        """
        return select_str

    def _from(self):
        from_str = """
            customer_list CL
                INNER JOIN route_detail RD on RD.id = CL.detail_id
                INNER JOIN route R on R.id = RD.route_id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                CL.customer_id,
                CL.result,
                RD.route_id,
                RD.date,
                RD.state,
                RD.comercial_id,
                R.type,
                R.day_id,
                R.state

        """
        return group_by_str

    def init(self, cr):
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(),
                    self._group_by()))
