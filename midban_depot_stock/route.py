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
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm


class route_zip(models.Model):
    _name = 'route.zip'
    _description = "List of Zip codes covered by route"
    _rec_name = 'code'

    code = fields.Char('Code', size=32, required=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Zip Code can not be repeated.')
    ]


class route(models.Model):
    _name = 'route'
    _description = 'Route Model'
    _rec_name = 'code'

    code = fields.Char('Code', size=32, required=True)
    name = fields.Char('Name', size=255, required=True)
    # 'vehicle_id': fields.many2one('stock.vehicle', 'Vehicle',
    #                               required=True),
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active')],
                             string="State", readonly=True,
                             default='draft')
    next_dc = fields.Integer('Next Drop Code', readonly=True,
                             required=True, default=1)
    # 'route_days_ids': fields.many2many('week.days',
    #                                    'routedays_week_days_rel',
    #                                    'route_id',
    #                                    'route_days_id',
    #                                    'Route Days'),
    day_id = fields.Many2one('week.days', 'Week_day', required=True)
    type = fields.Selection([('auto_sale', 'Auto Sale'),
                            ('comercial', 'Comercial'),
                            ('delivery', 'Delivery'),
                            ('ways', 'Ways'),
                            ('other', 'Other')], 'Type', required=True,
                            default='comercial')
    comercial_id = fields.Many2one('res.users', 'Comercial')
    zip_ids = fields.Many2many('route.zip', 'route_zip_codes_rel',
                               'route_id', 'route_zip_id', 'Zip codes',
                               required=True)
    detail_ids = fields.One2many('route.detail', 'route_id')

    @api.onchange('zip_ids')
    @api.multi
    def onchange_zip_ids(self):
        """
        Check there is no same zip code in a route of same day and same type.
        """
        res = {}
        warning = False
        if self.zip_ids:
            zip_codes = [x.code for x in self.zip_ids]
            domain = [('day_id', '=', self.day_id.id),
                      ('type', '=', self.type),
                      ('code', '!=', self.code)]
            route_objs = self.search(domain)
            if route_objs:
                not_check_more = False
                for route in route_objs:
                    for zip_c in route.zip_ids:
                        if zip_c.code in zip_codes:
                            warning = {
                                'title': _('Warning!'),
                                'message': _('The zip code %s is already \
                                              assigned in the\
                                              route %s. Change it or you can \
                                              not save de \
                                              route' % (zip_c.code,
                                                        route.code))}
                            not_check_more = True
                    if not_check_more:
                        break
        if warning:
            res['warning'] = warning
        return res

    @api.one
    def write(self, vals):
        """
        Overwrite to Check there is no same zip code in a route of same day
        and same type.
        """
        if vals.get('zip_ids', False):
            zip_ids = vals['zip_ids'][0][2]
            zip_objs = self.env['route.zip'].browse(zip_ids)
            zip_codes = [x.code for x in zip_objs]
            domain = [('day_id', '=', self.day_id.id),
                      ('type', '=', self.type),
                      ('code', '!=', self.code)]

            route_objs = self.search(domain)
            if route_objs:
                for route_obj in route_objs:
                    for zip_c in route_obj.zip_ids:
                        if zip_c.code in zip_codes:
                            raise except_orm(_('Error'),
                                             _('The zip code %s is already \
                                               assigned in the\
                                               route %s. Change it or you can \
                                               can not save th \
                                               route' % (zip_c.code,
                                                         route_obj.code)))
        res = super(route, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        if vals.get('zip_ids', False):
            zip_ids = vals['zip_ids'][0][2]
            zip_objs = self.env['route.zip'].browse(zip_ids)
            zip_codes = [x.code for x in zip_objs]
            domain = [('day_id', '=', vals['day_id']),
                      ('type', '=', vals['type']),
                      ('code', '!=', vals['code'])]

            route_objs = self.search(domain)
            if route_objs:
                for route_obj in route_objs:
                    for zip_c in route_obj.zip_ids:
                        if zip_c.code in zip_codes:
                            raise except_orm(_('Error'),
                                             _('The zip code %s is already \
                                               assigned in the\
                                               route %s. Change it or you can \
                                               can not save th \
                                               route' % (zip_c.code,
                                                         route_obj.code)))
        res = super(route, self).create(vals)
        return res

    @api.multi
    def set_active(self):
        self.state = 'active'

    @api.multi
    def set_draft(self):
        self.state = 'draft'

    @api.multi
    def reset_drop_code(self):
        self.next_dc = 1


class route_detail(models.Model):
    _name = 'route.detail'
    _description = "Detail for a route of one day"
    _rec_name = 'route_id'

    route_id = fields.Many2one('route', 'Route')
    date = fields.Date('Date')
    state = fields.Selection([('pending', 'Pending'),
                              ('on_course', 'On course'),
                              ('cancelled', 'Cancelled'),
                              ('closed', 'Closed')],
                             string="State",
                             default='pending')
    customer_ids = fields.One2many('customer.list', 'detail_id',
                                   'Customer List')

    @api.multi
    def set_cancelled(self):
        self.state = 'cancelled'

    @api.multi
    def set_closed(self):
        self.state = 'closed'

    @api.multi
    def set_pending(self):
        self.state = 'pending'


class customer_list(models.Model):
    _name = 'customer.list'
    _description = "Order of customer to visit"
    _rec_name = 'sequence'

    detail_id = fields.Many2one('route.detail', 'Detail')
    sequence = fields.Integer('Order')
    customer_id = fields.Many2one('res.partner', 'Customer',
                                  domain=[('customer', '=', True)],
                                  required=True)
    result = fields.Selection([('pending', 'Pending'),
                               ('sale_done', 'Sale done')],
                              string="result",
                              default='pending')
