# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class get_route_detail_wzd(models.TransientModel):
    _name = 'get.route.detail.wzd'

    start_date = fields.Date('Start Date', default=fields.Date.today())
    end_date = fields.Date('End Date', default=fields.Date.today())
    item_ids = fields.One2many('item.create.route', 'wzd_id',
                               'Selected Routes')

    @api.model
    def default_get(self, fields_list):
        """
        Get marked routes and his last pending date to show loaded in the
        wizard of create detailed routes.
        """
        res = super(get_route_detail_wzd, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        created_items_ids = []
        if active_ids:
            for route_id in active_ids:
                route_obj = self.env['route'].browse(route_id)
                last_date = route_obj.get_last_pending_date()
                vals = {
                    'route_id': route_id,
                    'last_pending_date': last_date and last_date[0] or False
                }
                item_obj = self.env['item.create.route'].create(vals)
                created_items_ids.append(item_obj.id)
            res.update({'item_ids': created_items_ids})
        return res

    @api.multi
    def create_route_details(self):
        """
        Create deatils of routes based on the wizard dates and the regularity
        defined in the customers.
        """
        if not self.item_ids:
            raise except_orm(_('Error'), _('No routes to shedule.'))
        start_date = self.start_date
        end_date = self.end_date
        for item in self.item_ids:
            start_date = item.start_date and item.start_date or start_date
            end_date = item.end_date and item.end_date or end_date
            route = item.route_id
            route.calc_route_details(start_date, end_date)
        return


class item_create_route(models.TransientModel):
    _name = 'item.create.route'

    wzd_id = fields.Many2one('get.route.detail.wzd', 'Wizard')
    route_id = fields.Many2one('route', 'Route', required=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    last_pending_date = fields.Date('Last Pending Date', readonly=True)
