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
from datetime import datetime, timedelta
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
    # next_dc = fields.Integer('Next Drop Code', readonly=True,
    #                          required=True, default=1)
    day_id = fields.Many2one('week.days', 'Week_day', required=True)
    type = fields.Selection([('auto_sale', 'Auto Sale'),
                            ('comercial', 'Comercial'),
                            ('delivery', 'Delivery'),
                            ('telesale', 'Telesale'),
                            ('ways', 'Ways'),
                            ('other', 'Other')], 'Type', required=True,
                            default='comercial')
    comercial_id = fields.Many2one('res.users', 'Responsible')
    bzip_ids = fields.Many2many('res.better.zip', 'better_zip_routes_rel',
                                'route_id', 'zip_id', 'Zip codes')
    detail_ids = fields.One2many('route.detail', 'route_id')
    partner_ids = fields.One2many('partner.route.info', 'route_id',
                                  'Customers', ondelete='cascade')
    active = fields.Boolean('Active', default=True)

    @api.onchange('bzip_ids')
    @api.multi
    def onchange_bzip_ids(self):
        """
        Check there is no same zip code in a route of same day and same type.
        """
        res = {}
        warning = False
        if self.bzip_ids:
            bzip_codes = [x.name for x in self.bzip_ids]
            domain = [('day_id', '=', self.day_id.id),
                      ('type', '=', self.type),
                      ('state', '=', 'active'),
                      ('name', '!=', self.name)]
            if self.id:
                domain.append(('id', '!=', self.id))
            route_objs = self.search(domain)
            if route_objs:
                not_check_more = False
                for route in route_objs:
                    for bzip_c in route.bzip_ids:
                        if bzip_c.name in bzip_codes:
                            warning = {
                                'title': _('Warning!'),
                                'message': _('The zip code %s is already \
                                              assigned in the\
                                              route %s. Change it or you can \
                                              not save de \
                                              route' % (bzip_c.name,
                                                        route.name))}
                            not_check_more = True
                    if not_check_more:
                        break
        # Check only if configured
        # self._check_partner_zip_in_route(force=True)
        if warning:
            res['warning'] = warning
        return res

    @api.multi
    def write(self, vals):
        """
        Overwrite to Check there is no same zip code in a route of same day
        and same type.
        """
        for r in self:
            day_id = vals.get('day_id', False) and vals['day_id'] or \
                r.day_id.id
            type = vals.get('type', False) and vals['type'] or r.type
            bzip_ids = vals.get('bzip_ids', False) and vals['bzip_ids'][0][2] or \
                [x.id for x in r.bzip_ids]
            bzip_objs = r.env['res.better.zip'].browse(bzip_ids)
            if bzip_objs and r.state == 'active':
                bzip_codes = [x.name for x in bzip_objs]
                domain = [('day_id', '=', day_id),
                          ('type', '=', type),
                          ('id', '!=', r.id),
                          ('state', '=', 'active')]

                route_objs = r.search(domain)
                if route_objs:
                    for route_obj in route_objs:
                        for bzip_c in route_obj.bzip_ids:
                            if bzip_c.name in bzip_codes:
                                raise except_orm(_('Error'),
                                                 _('The zip code %s is already \
                                                   assigned in the\
                                                   route %s. Change it or you \
                                                   can \
                                                   can not save th \
                                                   route' % (bzip_c.name,
                                                             route_obj.code)))
        res = super(route, self).write(vals)
        return res

    @api.one
    def unlink(self):
        """
        Delete de partner_route_info model in the partners side, and de detail
        routes
        """
        if self.state == 'active':
            raise except_orm(_('Error!'), _('Actives routes can not be \
                                            deleted. Put it in draft state'))
        for p in self.partner_ids:
            if p.route_id.id == self.id:
                p.unlink()

        for d in self.detail_ids:
            d.unlink()
        res = super(route, self).unlink()
        return res

    @api.one
    def set_active(self):
        """
        If there is a route of same day and same type with the same zip codes,
        (some of them), the route can not be activated.
        """
        if self.bzip_ids:
            bzip_codes = [x.name for x in self.bzip_ids]
            domain = [('day_id', '=', self.day_id.id),
                      ('type', '=', self.type),
                      ('id', '!=', self.id),
                      ('state', '=', 'active')]

            route_objs = self.search(domain)
            if route_objs:
                for route_obj in route_objs:
                    for bzip_c in route_obj.bzip_ids:
                        if bzip_c.name in bzip_codes:
                            raise except_orm(_('Error'),
                                             _('The zip code %s is already \
                                               assigned in the\
                                               route %s. It is no permited \
                                               routes of same type and same \
                                               day with the same zip \
                                               codes' % (bzip_c.name,
                                                         route_obj.code)))
        self.state = 'active'

    @api.multi
    def copy(self, default=None):
        res = super(route, self).copy(default=default)
        # create a new partner_info model equals to the old
        for p_info in self.partner_ids:
            new_p_info = p_info.copy()
            new_p_info.route_id = res.id
        return res

    @api.multi
    def set_draft(self):
        self.state = 'draft'

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
        # Create a detail for the date and add the customer to the list
        if detail_objs:
            detail_objs.unlink()
        for p_info in self.partner_ids:
            reg = p_info.regularity
            if p_info.init_date:  # Get specific date start
                dt_sta = datetime.strptime(p_info.init_date, FORMAT)
                # Check Dates Again
                # if not self._valid_dates(dt_sta, dt_end):
                #     raise except_orm(_('Error'),
                #                      _('Date range not valid.'))
            interval = 1 if reg == '1_week' else (2 if reg == '2_week' else
                                                  (3 if reg == '3_week' else
                                                      (4 if reg == '4_week' else
                                                         (1 if reg == '3yes_1no' else
                                                           (1 if reg == '3no_1yes' else
                                                            (1 if reg == '2yes_2no'
                                                          else False))))))

            # To include end date in rrules
            if dt_end.weekday() == day_number:
                dt_end = dt_end + timedelta(days=1)
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

            to_remove = []

            if reg == '3yes_1no':
                count = 0
                for date in customer_dates:
                    count += 1
                    if count == 4:
                        to_remove.append(date)
                        count = 0
            if reg == '2yes_2no':
                count = 0
                for date in customer_dates:
                    count += 1
                    if count >= 3:
                        if count == 3:
                            to_remove.append(date)
                        else:
                            to_remove.append(date)
                            count = 0
            if reg == '3no_1yes':
                count = 0
                for date in customer_dates:
                    count += 1
                    if count in (1,2,3):
                        to_remove.append(date)
                    else:
                        count = 0
            for date in to_remove:
                customer_dates.remove(date)

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
                if self.type != 'telesale':
                    # Add customer to customer lists of detail
                    vals = {
                        'detail_id': det_obj.id,
                        'sequence': p_info.sequence,
                        'customer_id': p_info.partner_id.id,
                        # 'result': 'pending'
                    }
                    self.env['customer.list'].create(vals)
                # Create the list of calls
                else:
                    det_name = det_obj.name_get()[0][1]
                    vals = {
                        'name': _("Telesale Call ") + p_info.partner_id.name,
                        'partner_id': p_info.partner_id.id,
                        'detail_id': det_obj.id,
                        'description': _("Scheduled Call from %s" % det_name),
                        'date': det_obj.date + " 06:00:00"
                    }
                    self.env['crm.phonecall'].create(vals)


class route_detail(models.Model):
    _name = 'route.detail'
    _description = "Detail for a route of one day"
    _rec_name = 'route_id'
    _order = 'date'

    # @api.multi
    # @api.depends('route_id', 'date')
    # def _get_detail_name_str(self):
    #     """
    #     Calc name str
    #     """
    #     print "_get_detail_name_str"
    #     for detail in self:
    #         detail.detail_name_str = detail.route_id.code + " " + detail.date

    @api.one
    def _get_detail_name_str(self):
        """
        Calc name str
        """
        print "_get_detail_name_str"
        self.detail_name_str = self.route_id.code + " " + self.date

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
    call_ids = fields.One2many('crm.phonecall', 'detail_id', 'Call list')
    comercial_id = fields.Many2one('res.users', 'Responsible',
                                    related='route_id.comercial_id',
                                    readonly=True,
                                    store=True)
    delivery_man_id = fields.Many2one('res.users', 'Delivery Man')
    route_type = fields.Selection([('auto_sale', 'Auto Sale'),
                                   ('comercial', 'Comercial'),
                                   ('delivery', 'Delivery'),
                                   ('telesale', 'Telesale'),
                                   ('ways', 'Ways'),
                                   ('other', 'Other')], 'Type',
                                  related='route_id.type',
                                  store=True,
                                  readonly=True)
    detail_name_str = fields.Char("Detail name", readonly=True,
                                  compute='_get_detail_name_str',
                                  store=True)

    def view_account_moves(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        '''
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'midban_depot_stock', 'action_payments_route'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)

        partner_ids = []
        move_obj = self.pool.get('account.move.line')
        pick_obj = self.pool.get('stock.picking')
        #for route_detail in self.browse(cr, uid, ids, context=context):
        print ids
        pick_ids = pick_obj.search(cr, uid, [('picking_type_id.code', '=', 'outgoing') ,
                                             ('route_detail_id', 'in', ids)])
        print "Pickings"
        print pick_ids
        partner_ids += [picking.partner_id.id for picking in pick_obj.browse(cr,uid, pick_ids)]
        print "Partners"
        print partner_ids
        domain = [('partner_id', 'in', partner_ids),
                ('account_id.type', '=', 'receivable'),
                ('reconcile_id','=', False)]
        print domain
        move_ids = move_obj.search(cr, uid, domain, context=context)
        #override the context to get rid of the default filtering on picking type
        action['context'] = {}
        #choose the view_mode accordingly
        action['domain'] = "[('id','in',[" + ','.join(map(str, move_ids)) + "])]"
        return action

    @api.multi
    def set_cancelled(self):
        self.state = 'cancelled'

    @api.multi
    def set_pending(self):
        self.state = 'pending'

    @api.multi
    def set_on_course(self):
        self.state = 'on_course'

    @api.multi
    def set_closed(self):
        self.state = 'closed'

    @api.one
    def unlink(self):
        if self.route_id.state == 'active':
            if self.state not in ['pending'] or \
                    self.date < time.strftime(FORMAT):
                if self.date < time.strftime(FORMAT):
                    msg = _('Detail route for day %s can not be deleted \
                             because is a past date' % self.date)
                else:
                    msg = _('Detail route for day %s with state is %s can not \
                             be deleted. Only pending routes can be\
                             deleted' % (self.date, self.state))
                raise except_orm(_('ERROR'), msg)
        else:
            for rec in self.customer_ids:
                rec.unlink()
            for rec in self.call_ids:
                rec.unlink()
        res = super(route_detail, self).unlink()
        return res

    @api.model
    def create(self, vals):
        if vals.get('route_id', False) and not vals.get('comercial_id'):
            route_obj = self.env['route'].browse(vals['route_id'])
            if route_obj.comercial_id:
                vals['comercial_id'] = route_obj.comercial_id.id
        res = super(route_detail, self).create(vals)
        return res

    @api.multi
    def name_get(self):
        res = []
        for detail in self:
            date_split = detail.date.split('-')
            date = date_split[2] + "-" + date_split[1] + "-" + date_split[0]
            name = detail.route_id.code + ", " + date
            res.append((detail.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        res = super(route_detail, self).name_search(name, args=args,
                                                    operator=operator,
                                                    limit=limit)
        args.append(('detail_name_str', operator, name))
        recs = self.search(args)
        for r in recs:
            if r.date < time.strftime("%Y-%m-%d"):
                recs -= r
        res = recs.name_get()
        return res


class customer_list(models.Model):
    _name = 'customer.list'
    _description = "Order of customer to visit"
    _rec_name = 'detail_id'

    detail_id = fields.Many2one('route.detail', 'Detail')
    sequence = fields.Integer('Order')
    customer_id = fields.Many2one('res.partner', 'Customer',
                                  domain=[('customer', '=', True)],
                                  required=True)
    phone = fields.Char('Phone', related="customer_id.phone", readonly=True)
    sale_id = fields.Many2one('sale.order', 'Order', readonly=True,
                              help='is linked when confirm a order with this\
                              detail route')
    result = fields.Selection([('sale_done', 'Sale done'),
                               ('pending', 'Pending'),
                               ('visited_no_order', 'Visited without order'),
                               ('closed_day', 'Closed day'),
                               ('closed_holidays', 'Holidays'),
                               ('closed_reform', 'Closed Reform'),
                               ('no_visited', 'No visited'),
                               ('delivered_ok', 'Delivered OK'),
                               ('delivered_issue', 'Delivered with issue')],
                              string="result", default='pending')
