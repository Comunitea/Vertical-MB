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
from datetime import datetime
from dateutil.rrule import rrule, WEEKLY
import time


FORMAT = "%Y-%m-%d"


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
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active')],
                             string="State", readonly=True,
                             default='draft')
    next_dc = fields.Integer('Next Drop Code', readonly=True,
                             required=True, default=1)
    day_id = fields.Many2one('week.days', 'Week_day', required=True)
    type = fields.Selection([('auto_sale', 'Auto Sale'),
                            ('comercial', 'Comercial'),
                            ('delivery', 'Delivery'),
                            ('telesale', 'Telesale'),
                            ('ways', 'Ways'),
                            ('other', 'Other')], 'Type', required=True,
                            default='comercial')
    comercial_id = fields.Many2one('res.users', 'Comercial')
    zip_ids = fields.Many2many('route.zip', 'route_zip_codes_rel',
                               'route_id', 'route_zip_id', 'Zip codes',
                               required=True)
    detail_ids = fields.One2many('route.detail', 'route_id')
    partner_ids = fields.One2many('partner.route.info', 'route_id',
                                  'Customers')

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
            for p_info in self.partner_ids:
                if not p_info.partner_id.zip:
                    raise except_orm(_('Error'),
                                     _('Customer %s has not zip \
                                        code' % p_info.partner_id.name))
                if p_info.partner_id.zip not in zip_codes:
                    raise except_orm(_('Error'),
                                     _('Zip code of customer %s (%s) not \
                                      in the route' % (p_info.partner_id.name,
                                                       p_info.partner_id.zip)))
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

            for p_info in self.partner_ids:
                    if not p_info.partner_id.zip:
                        raise except_orm(_('Error'),
                                         _('Customer %s has not zip \
                                            code' % p_info.partner_id.name))
                    if p_info.partner_id.zip not in zip_codes:
                        raise except_orm(_('Error'),
                                         _('Zip code of customer %s (%s) not \
                                          in the \
                                          route' % (p_info.partner_id.name,
                                                    p_info.partner_id.zip)))
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
                                               can not save the \
                                               route' % (zip_c.code,
                                                         route_obj.code)))
            for p_info in self.partner_ids:
                if not p_info.partner_id.zip:
                    raise except_orm(_('Error'),
                                     _('Customer %s has not zip \
                                        code' % p_info.partner_id.name))
                if p_info.partner_id.zip not in zip_codes:
                    raise except_orm(_('Error'),
                                     _('Zip code of customer %s (%s) not \
                                      in the route' % (p_info.partner_id.name,
                                                       p_info.partner_id.zip)))
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

    @api.one
    def get_last_pending_date(self):
        domain = [
            ('route_id', '=', self.id),
            ('state', '=', 'pending'),
        ]
        last_pending = self.env['route.detail'].search(domain,
                                                       order="date desc",
                                                       limit=1)
        return last_pending and last_pending.date or False

    def _valid_dates(self, dt_sta, dt_end):
        res = True
        format_date = FORMAT
        today_str = datetime.strftime(datetime.today(), format_date)
        today = datetime.strptime(today_str, format_date)
        if (dt_sta < today or dt_end < dt_sta):
            res = False
        return res

    @api.one
    def calc_route_details(self, start_date, end_date, delete, recalc=True):
        dt_sta = datetime.strptime(start_date, FORMAT)
        day_number = self.day_id.sequence - 1
        dt_end = datetime.strptime(end_date, FORMAT)

        # Check Dates
        if not self._valid_dates(dt_sta, dt_end):
            raise except_orm(_('Error'),
                             _('Date range not valid.'))

        if not self.partner_ids and not recalc:
            raise except_orm(_('Error'),
                             _('No customers assigned to the route'))

        domain = [
            ('date', '>=', start_date),
            ('route_id', '=', self.id),
        ]
        if not delete:
            domain.append(('date', '<=', end_date))
        detail_objs = self.env['route.detail'].search(domain)
        # Create a detail for the date and add the customer to de list
        if detail_objs:
            detail_objs.unlink()
        for p_info in self.partner_ids:
            reg = p_info.regularity
            interval = 1 if reg == '1_week' else (2 if reg == '2_week' else
                                                  (3 if reg == '3_week' else
                                                      (4 if reg == '4_week'
                                                          else False)))
            rrules = rrule(WEEKLY, interval=interval,
                           byweekday=day_number).between(dt_sta, dt_end,
                                                         inc=True)
            customer_dates = [datetime.strftime(x, FORMAT) for x in rrules]
            if not customer_dates and not recalc:
                raise except_orm(_('Error'),
                                 _('Imposible to schedule dates between %s and \
                                    %s with regularity of %s \
                                    week(s)' % (start_date, end_date,
                                                str(interval))))
            for date in customer_dates:
                domain = [
                    ('date', '=', date),
                    ('route_id', '=', p_info.route_id.id),
                ]
                detail_objs = self.env['route.detail'].search(domain)
                # Create a detail for the date and add the customer to de list
                if not detail_objs:
                    vals = {
                        'route_id': p_info.route_id.id,
                        'date': date,
                        'state': 'pending',
                    }
                    det_obj = self.env['route.detail'].create(vals)
                    # Add customer to customer lists of detail
                    vals = {
                        'detail_id': det_obj.id,
                        'sequence': p_info.sequence,
                        'customer_id': p_info.partner_id.id,
                        # 'result': 'pending'
                    }
                    self.env['customer.list'].create(vals)

                # Detail obj already exists for the date, re-write it
                else:
                    if len(detail_objs) > 1:  # Bad situation
                        raise except_orm(_('Error'),
                                         _('2 details of same day for same \
                                           route'))
                    det_obj = detail_objs[0]
                    if det_obj.state in ['done', 'on_course']:
                        raise except_orm(_('Error'),
                                         _('Can not re-schedule a route in %s \
                                           state' % det_obj.state))
                    # Put the existing detail to pending
                    det_obj.write({'state': 'pending'})
                    # Check if customer is already in customers lists
                    domain = [('detail_id', '=', det_obj.id),
                              ('customer_id', '=', p_info.partner_id.id)]
                    cust_objs = self.env['customer.list'].search(domain)
                    if cust_objs:
                        cust_objs.unlink()  # Delete the customer list regiser
                    # Create a customer list record for the detail
                    vals = {
                        'detail_id': det_obj.id,
                        'sequence': p_info.sequence,
                        'customer_id': p_info.partner_id.id
                    }
                    self.env['customer.list'].create(vals)


class route_detail(models.Model):
    _name = 'route.detail'
    _description = "Detail for a route of one day"
    _rec_name = 'route_id'
    _order = 'date'

    route_id = fields.Many2one('route', 'Route', required=True)
    date = fields.Date('Date', required=True)
    state = fields.Selection([('pending', 'Pending'),
                              ('on_course', 'On course'),
                              ('cancelled', 'Cancelled'),
                              ('closed', 'Closed')],
                             string="State",
                             required=True,
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

    @api.one
    def unlink(self):
        if self.state not in ['pending'] or self.date < time.strftime(FORMAT):
            if self.date < time.strftime(FORMAT):
                msg = _('Detail route for day %s can not be deleted because is\
                         a past date' % self.date)
            else:
                msg = _('Detail route for day %s with state is %s can not be \
                         deleted. Only pending routes can be\
                         deleted' % (self.date, self.state))
            raise except_orm(_('ERROR'), msg)
        res = super(route_detail, self).unlink()
        return res


class customer_list(models.Model):
    _name = 'customer.list'
    _description = "Order of customer to visit"
    _rec_name = 'sequence'

    detail_id = fields.Many2one('route.detail', 'Detail')
    sequence = fields.Integer('Order')
    customer_id = fields.Many2one('res.partner', 'Customer',
                                  domain=[('customer', '=', True)],
                                  required=True)
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
                              string="result")
