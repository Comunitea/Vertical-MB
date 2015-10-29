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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import models, fields as fields2, api
from openerp.exceptions import except_orm
import time

FORMAT = "%Y-%m-%d"


class partner_route_info(models.Model):
    _name = 'partner.route.info'
    _rec_name = 'route_id'
    _order = 'sequence'

    @api.one
    # @api.depends('invoice_line.price_subtotal', 'tax_line.amount',
    #              'amount_discount')
    def _compute_dates(self):
        """
        Calc dates
        """
        domain = [
            ('route_id', '=', self.route_id.id),
            ('state', '=', 'closed'),
            ('date', '<', time.strftime(FORMAT)),
        ]
        detail_objs = self.env['route.detail'].search(domain,
                                                      order="date desc")
        if detail_objs:
            self.last_date = detail_objs[0].date

        domain = [
            ('route_id', '=', self.route_id.id),
            ('state', '=', 'pending'),
            ('date', '>=', time.strftime(FORMAT)),
        ]
        detail_objs = self.env['route.detail'].search(domain,
                                                      order="date asc")
        if detail_objs:
            self.next_date = detail_objs[0].date

    sequence = fields2.Integer('Order')
    partner_id = fields2.Many2one('res.partner', 'Customer',
                                  domain=[('customer', '=', True)])
    regularity = fields2.Selection([('1_week', '1 Week'),
                                    ('2_week', '2 Weeks'),
                                    ('3_week', '3 Weeks'),
                                    ('4_week', '4 Weeks'),
                                    ('3yes_1no', '3 Weeks Yes, 1 Week No'),
                                    ('2yes_2no', '2 Weeks Yes, 2 Week No'),
                                    ('3no_1yes', '3 Weeks No, 1 Week Yes')], 'Regularity',
                                   default="1_week", required=True)
    last_date = fields2.Date('Last Date', compute='_compute_dates',
                             readonly=True)
    next_date = fields2.Date('Next Date', compute='_compute_dates',
                             readonly=True)
    init_date = fields2.Date('Init Date', readonly=False)
    route_id = fields2.Many2one('route', 'Route')
    day_id = fields2.Many2one('week.days', 'Week day', readonly=True,
                              related="route_id.day_id")
    type = fields2.Selection([('auto_sale', 'Auto Sale'),
                             ('comercial', 'Comercial'),
                             ('delivery', 'Delivery'),
                             ('telesale', 'Telesale'),
                             ('ways', 'Ways'),
                             ('other', 'Other')], 'Type', readonly=True,
                             related='route_id.type')

    @api.onchange('partner_id', 'route_id')
    @api.multi
    def onchange_partner_id(self):
        """
        Warning if you select a customer which zip code is not in the route
        zip codes list.
        The if configurations let it you will be able to save the route.
        """
        res = {}
        warning = False
        if self.partner_id and self.route_id:
            if self.route_id.bzip_ids:
                bzip_codes = [x.name for x in self.route_id.bzip_ids]
                if not self.partner_id.zip:
                    warning = {
                        'title': _('Warning!'),
                        'message': _('Customer %s must have a zip code. \
                                     ' % self.partner_id.name),
                    }
                elif self.partner_id.zip not in bzip_codes:
                    warning = {
                        'title': _('Warning!'),
                        'message': _('The zip code %s is not in the route zip \
                                      codes list' % self.partner_id.zip),
                    }
            if self.route_id.type not in ['telesale', 'delivery']:
                route_obj = self.env['route'].search([('name', '=',
                                                     self.route_id.name)])
                if route_obj:
                    domain = [
                        ('route_id', '!=', route_obj.id),
                        ('partner_id', '=', self.partner_id.id),
                        ('route_id.type', 'not in', ['telesale', 'delivery']),
                        ('route_id.comercial_id', '!=',
                            self.route_id.comercial_id.id),
                    ]
                    info_objs = self.search(domain)
                    if info_objs:
                        warning = {
                            'title': _('Warning!'),
                            'message': _('Customer %s is asigned to a route of \
                                          other comercial' %
                                         self.partner_id.name),
                        }
            if self.route_id.type in ['delivery']:
                close_days = [wd.sequence for wd in self.partner_id.close_days]
                route_wd = self.route_id.day_id.sequence
                if route_wd in close_days:
                    warning = {
                        'title': _('Warning!'),
                        'message': _('You are assigning a route for a \
                                        partner closed  day '),
                    }
        if warning:
            res['warning'] = warning
        return res

    @api.one
    def _recalculate_routes(self, route_new, route_old):
        routes = []
        if route_new:
            routes.append(route_new)
        if route_old:
            routes.append(route_old)
        for route in routes:
            today = time.strftime(FORMAT)
            domain = [
                ('route_id', '=', route.id),
                ('date', '>=', today),
            ]
            details = self.env['route.detail'].search(domain,
                                                      order="date desc")
            if details:
                last_date = details[0].date
                route.calc_route_details(today, last_date, False)
        return

    @api.multi
    def _get_route_settings(self):
        """
        Returns a dict with configuration values
        """
        res = {}
        domain = [('key', '=', 'check.route.zip')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        if param_obj:
            value = True if param_obj.value == 'True' else False
            res['check_route_zip'] = value

        domain = [('key', '=', 'check.customer.comercial')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        if param_obj:
            value = True if param_obj.value == 'True' else False
            res['check_customer_comercial'] = value
        return res

    @api.one
    def write(self, vals):
        """
        Overwrite to Check there if partnerzip code is in route zip code, if
        configured like that
        """
        t_route = self.env['route']
        t_partner = self.env['res.partner']
        partner_id = vals.get('partner_id', False) and vals['partner_id'] or \
            self.partner_id.id
        route_id = vals.get('route_id', False) and vals['route_id'] or \
            self.route_id.id
        partner_obj = t_partner.browse(partner_id)
        route_obj = t_route.browse(route_id)
        partner_obj = t_partner.browse(partner_id)
        route_obj = t_route.browse(route_id)
        route_bzip_codes = [x.name for x in route_obj.bzip_ids]
        settings = self._get_route_settings()
        # Check if customer zip is in route zips list
        check_zips = settings.get('check_route_zip', False)
        if check_zips:
            if not partner_obj.zip:
                raise except_orm(_('Error'), _('The customer has no zip code'))
            if partner_obj.zip not in route_bzip_codes:
                raise except_orm(_('Error'), _('Zip code %s of customer %s \
                                 is not included in the route \
                                 %s' % (partner_obj.zip, partner_obj.name,
                                        route_obj.name)))

        check_customers = settings.get('check_customer_comercial', False)
        # Check if there is no other route with same client and different
        # Comercial
        if check_customers:
            domain = [
                ('route_id', '!=', route_obj.id),
                ('partner_id', '=', partner_obj.id),
                ('route_id.type', 'not in', ['telesale', 'delivery']),
                ('route_id.comercial_id', '!=',
                    self.route_id.comercial_id.id),
            ]
            info_objs = self.search(domain)
            if info_objs:
                raise except_orm(_('Error'),
                                 _('Customer %s is asigned to a route of \
                                    other comercial' % partner_obj.name))
        old_route = False
        if vals.get('route_id', False) and self.route_id:
            old_route = self.route_id
        res = super(partner_route_info, self).write(vals)
        self._recalculate_routes(route_obj, old_route)
        return res

    @api.model
    def create(self, vals):
        """
        Overwrite to Check there if partnerzip code is in route zip code, if
        configured like that
        """
        t_route = self.env['route']
        t_partner = self.env['res.partner']
        partner_id = vals.get('partner_id', False) and vals['partner_id'] or \
            False
        route_id = vals.get('route_id', False) and vals['route_id'] or \
            False
        if partner_id and route_id:
            partner_obj = t_partner.browse(partner_id)
            route_obj = t_route.browse(route_id)
            route_bzip_codes = [x.name for x in route_obj.bzip_ids]
            settings = self._get_route_settings()
            check_zips = settings.get('check_route_zip', False)
            if check_zips:  # Configured to check
                if not partner_obj.zip:
                    raise except_orm(_('Error'),
                                     _('The customer has no zip code'))
                if partner_obj.zip not in route_bzip_codes:
                    raise except_orm(_('Error'),
                                     _('Zip code %s of customer %s \
                                     is not included in the route \
                                     %s' % (partner_obj.zip, partner_obj.name,
                                            route_obj.name)))

            check_customers = settings.get('check_customer_comercial', False)
            # Check if there is no other route with same client and different
            # Comercial
            if check_customers:
                if route_obj:
                    domain = [
                        ('route_id', '!=', route_obj.id),
                        ('partner_id', '=', partner_obj.id),
                        ('route_id.type', 'not in', ['telesale', 'delivery']),
                        ('route_id.comercial_id', '!=',
                            route_obj.comercial_id.id),
                    ]
                    info_objs = self.search(domain)
                    if info_objs:
                        raise except_orm(_('Error'),
                                         _('Customer %s is asigned to a route \
                                            of other \
                                            comercial' % partner_obj.name))
        res = super(partner_route_info, self).create(vals)
        route_obj = t_route.browse(route_id)
        res._recalculate_routes(route_obj, False)
        return res

    @api.one
    def unlink(self):
        route_obj = self.route_id
        res = super(partner_route_info, self).unlink()
        self._recalculate_routes(route_obj, False)
        return res


class resPartner(models.Model):
    _inherit = 'res.partner'

    route_part_ids = fields2.One2many('partner.route.info', 'partner_id',
                                      'Assigned Routes')

    @api.multi
    def get_next_route_detail(self, route_type=False):
        """
        Get the closest detail route obj of all defined partner routes,
        if route_type passed we search details of this route type only
        """
        detail_obj = False
        if self.route_part_ids:
            detail_t = self.env['route.detail']
            partner_routes = [x.route_id.id for x in self.route_part_ids
                              if x.route_id.type == 'delivery']
            domain = [
                ('route_id', 'in', partner_routes),
                ('date', '>', time.strftime("%Y-%m-%d"))
            ]
            if route_type:
                domain.append(('route_type', '=', route_type))
            detail_objs = detail_t.search(domain, order="date")
            for detail in detail_objs:
                for cust in detail.customer_ids:
                    if cust.customer_id.id == self.id:
                        detail_obj = detail
                if detail_obj:
                    break
        return detail_obj

    @api.multi
    def any_detail_founded(self):
        res = False
        detail = self.get_next_route_detail()
        if detail:
            res = {'detail_date': detail.date}
        return res

    def search(self, cr, user, args, offset=0, limit=None, order=None,
               context=None, count=False):
        if context is None:
            context = {}
        domain = [('key', '=', 'check.route.zip')]
        param_ids = self.pool['ir.config_parameter'].search(cr, user, domain)
        if param_ids:
            param_obj = self.pool['ir.config_parameter'].browse(cr, user,
                                                                param_ids[0])
            value = True if param_obj.value == 'True' else False
            if context.get('route_id', False) and value:
                route_obj = self.pool['route'].browse(cr, user,
                                                      context['route_id'])
                bzip_codes = [x.name for x in route_obj.bzip_ids]
                args.append(['zip', 'in', bzip_codes])
        return super(resPartner, self).search(cr, user, args,
                                              offset=offset,
                                              limit=limit,
                                              order=order,
                                              context=context,
                                              count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        res = super(resPartner, self).name_search(name, args=args,
                                                  operator=operator,
                                                  limit=limit)
        domain = [('key', '=', 'check.route.zip')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = True if param_obj.value == 'True' else False
        if self._context.get('route_id', False) and value:
            args.append(('name', operator, name))
            recs = self.search(args)
            res = recs.name_get()
        return res


# class res_partner(osv.Model):
#     _inherit = 'res.partner'
#     _columns = {
#         'trans_route_id': fields.many2one('route', 'Transport Route',
#                                           domain=[('state', '=', 'active')]),
#     }
#
#     @api.onchange('trans_route_id')
#     @api.multi
#     def onchange_route_id(self):
#         """
#         Check the delivery days of the customer and the route days.
#         If no common days raise a warning
#         raise a warning if some customer days are not in the transport route.
#         """
#         res = {}
#         warning = False
#         if not self.delivery_days_ids:
#             warning = {
#                 'title': _('Warning!'),
#                 'message': _('There is no delivery days in this customer!'),
#             }
#         elif not self.trans_route_id.route_days_ids:
#             warning = {
#                 'title': _('Warning!'),
#                 'message': _('There is no route days in the selected route!'),
#             }
#         else:
#             partner_days = set(self.delivery_days_ids)
#             route_days = set(self.trans_route_id.route_days_ids)
#             common_days = partner_days & route_days
#             if not common_days:
#                 warning = {
#                     'title': _('Warning!'),
#                     'message': _('Selected delivery days are not in the \
#                                  transport Route!'),
#                 }
#             else:
#                 diff_days = list(partner_days - common_days)
#                 diff_days = sorted(diff_days, key=lambda d: d.sequence)
#                 diff_days_str = ""
#                 for d in diff_days:
#                     if not diff_days_str:
#                         diff_days_str += d.name
#                     else:
#                         diff_days_str += "," + d.name
#                 if diff_days_str:
#                     warning = {
#                         'title': _('Warning!'),
#                         'message': _('The days %s are not in the selected \
#                                       transport route') % diff_days_str,
#                     }
#         if warning:
#             res['warning'] = warning
#         return res
#
#     @api.onchange('delivery_days_ids')
#     @api.multi
#     def onchange_delivery_days_ids(self):
#         """
#         Check the delivery days of the customer and the route days.
#         If no common days raise a warning
#         raise a warning if some customer days are not in the transport route.
#         """
#         res = {}
#         warning = False
#         if self.trans_route_id and self.trans_route_id.route_days_ids:
#             partner_days = set(self.delivery_days_ids)
#             route_days = set(self.trans_route_id.route_days_ids)
#             common_days = partner_days & route_days
#             if not common_days:
#                 warning = {
#                     'title': _('Warning!'),
#                     'message': _('Selected delivery days are not in the \
#                                  transport Route!'),
#                 }
#             else:
#                 diff_days = list(partner_days - common_days)
#                 diff_days = sorted(diff_days, key=lambda d: d.sequence)
#                 diff_days_str = ""
#                 for d in diff_days:
#                     if not diff_days_str:
#                         diff_days_str += d.name
#                     else:
#                         diff_days_str += "," + d.name
#                 if diff_days_str:
#                     warning = {
#                         'title': _('Warning!'),
#                         'message': _('The days %s are not in the selected \
#                                       transport route') % diff_days_str,
#                     }
#         if warning:
#             res['warning'] = warning
#         return res
