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
                                    ('4_week', '4 Weeks')], 'Regularity',
                                   default="1_week", required=True)
    last_date = fields2.Date('Last Date', compute='_compute_dates',
                             readonly=False)
    next_date = fields2.Date('Next Date', compute='_compute_dates',
                             readonly=False)
    route_id = fields2.Many2one('route', 'Route')

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

    @api.one
    def write(self, vals):
        """
        Overwrite to Check there if partnerzip code is in route zip code
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
        if not partner_obj.zip:
            raise except_orm(_('Error'), _('The customer has no zip code'))
        if partner_obj.zip not in route_bzip_codes:
            raise except_orm(_('Error'), _('Zip code %s of customer %s \
                             is not included in the route \
                             %s' % (partner_obj.zip, partner_obj.name,
                                    route_obj.name)))
        old_route = False
        if vals.get('route_id', False) and self.route_id:
            old_route = self.route_id
        res = super(partner_route_info, self).write(vals)
        self._recalculate_routes(route_obj, old_route)
        return res

    @api.model
    def create(self, vals):
        """
        Overwrite to Check there if partnerzip code is in route zip code
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
            if not partner_obj.zip:
                raise except_orm(_('Error'), _('The customer has no zip code'))
            if partner_obj.zip not in route_bzip_codes:
                raise except_orm(_('Error'), _('Zip code %s of customer %s \
                                 is not included in the route \
                                 %s' % (partner_obj.zip, partner_obj.name,
                                        route_obj.name)))
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
    def get_next_route_detail(self):
        detail_obj = False
        if self.route_part_ids:
            detail_t = self.env['route.detail']
            partner_routes = [x.route_id.id for x in self.route_part_ids
                              if x.route_id.type == 'delivery']
            domain = [
                ('route_id', 'in', partner_routes),
                ('date', '>', time.strftime("%Y-%m-%d"))
            ]
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
            res = True
        return res

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """ """
        # import ipdb; ipdb.set_trace()
        if self._context.get('route_id', False):
            route_obj = self.env['route'].browse(self._context['route_id'])
            bzip_codes = [x.name for x in route_obj.bzip_ids]
            args.append(['zip', 'in', bzip_codes])
        return super(resPartner, self).search(args,
                                              offset=offset,
                                              limit=limit,
                                              order=order,
                                              count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        # import ipdb; ipdb.set_trace()
        res = super(resPartner, self).name_search(name, args=args,
                                                  operator=operator,
                                                  limit=limit)
        if self._context.get('route_id', False):
            recs = self.search(args)
            res = recs.name_get()
        return res


class res_partner(osv.Model):
    _inherit = 'res.partner'
    _columns = {
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                          domain=[('state', '=', 'active')]),
    }

    @api.onchange('trans_route_id')
    @api.multi
    def onchange_route_id(self):
        """
        Check the delivery days of the customer and the route days.
        If no common days raise a warning
        raise a warning if some customer days are not in the transport route.
        """
        res = {}
        warning = False
        if not self.delivery_days_ids:
            warning = {
                'title': _('Warning!'),
                'message': _('There is no delivery days in this customer!'),
            }
        elif not self.trans_route_id.route_days_ids:
            warning = {
                'title': _('Warning!'),
                'message': _('There is no route days in the selected route!'),
            }
        else:
            partner_days = set(self.delivery_days_ids)
            route_days = set(self.trans_route_id.route_days_ids)
            common_days = partner_days & route_days
            if not common_days:
                warning = {
                    'title': _('Warning!'),
                    'message': _('Selected delivery days are not in the \
                                 transport Route!'),
                }
            else:
                diff_days = list(partner_days - common_days)
                diff_days = sorted(diff_days, key=lambda d: d.sequence)
                diff_days_str = ""
                for d in diff_days:
                    if not diff_days_str:
                        diff_days_str += d.name
                    else:
                        diff_days_str += "," + d.name
                if diff_days_str:
                    warning = {
                        'title': _('Warning!'),
                        'message': _('The days %s are not in the selected \
                                      transport route') % diff_days_str,
                    }
        if warning:
            res['warning'] = warning
        return res

    @api.onchange('delivery_days_ids')
    @api.multi
    def onchange_delivery_days_ids(self):
        """
        Check the delivery days of the customer and the route days.
        If no common days raise a warning
        raise a warning if some customer days are not in the transport route.
        """
        res = {}
        warning = False
        if self.trans_route_id and self.trans_route_id.route_days_ids:
            partner_days = set(self.delivery_days_ids)
            route_days = set(self.trans_route_id.route_days_ids)
            common_days = partner_days & route_days
            if not common_days:
                warning = {
                    'title': _('Warning!'),
                    'message': _('Selected delivery days are not in the \
                                 transport Route!'),
                }
            else:
                diff_days = list(partner_days - common_days)
                diff_days = sorted(diff_days, key=lambda d: d.sequence)
                diff_days_str = ""
                for d in diff_days:
                    if not diff_days_str:
                        diff_days_str += d.name
                    else:
                        diff_days_str += "," + d.name
                if diff_days_str:
                    warning = {
                        'title': _('Warning!'),
                        'message': _('The days %s are not in the selected \
                                      transport route') % diff_days_str,
                    }
        if warning:
            res['warning'] = warning
        return res
