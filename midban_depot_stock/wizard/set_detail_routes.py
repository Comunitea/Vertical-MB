# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Santi Argüeso <santi@comunitea.com>$
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
from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class SetDetailRoutes(models.TransientModel):

    _name = 'set.detail.routes'
    route_detail_id = fields.Many2one('route.detail', 'Detail route')

    @api.multi
    def set_details(self):
        active_ids = self.env.context['active_ids']
        out_pickings = self.env['stock.picking'].browse(active_ids)

        out_pickings.write({'route_detail_id': self.route_detail_id.id})
        # Display the assigned picks
        action_obj = self.env.ref('midban_depot_stock.action_replanning_picking_route')
        action = action_obj.read()[0]
        action['domain'] = str([('id', 'in', out_pickings._ids)])
        action['context'] = {}
        return action

    # @api.multi
    # def set_details(self):
    #     t_pick = self.env['stock.picking']
    #     active_ids = self.env.context['active_ids']
    #     out_pickings = t_pick.browse(active_ids)
    #     # Escribir min_date de la tuta en los de picks
    #     wh = self.env['stock.warehouse'].search([])[0]
    #     picks_totals = out_pickings
    #     detail_date = self.route_detail_id.date + " 19:00:00"
    #
    #     for pick in out_pickings:
    #         if pick.group_id:
    #             domain = [('state', 'in', ['confirmed', 'assigned']),
    #                       ('group_id', '=', pick.group_id.id),
    #                       ('picking_type_id', '=', wh.pick_type_id.id)]
    #             pick_objs = t_pick.search(domain)
    #             picks_totals += pick_objs
    #     picks_totals.write({'route_detail_id': self.route_detail_id.id,
    #                         'min_date': detail_date})
    #     # TODO ÑAPA parece que picks_totals no hace el out junto no lo escribe al out
    #     out_pickings.write({'min_date': detail_date})
    #     # Display the assigned picks
    #     action_obj = self.env.ref('midban_depot_stock.action_replanning_picking_route')
    #     action = action_obj.read()[0]
    #     action['domain'] = str([('id', 'in', out_pickings._ids)])
    #     action['context'] = {}
    #     return action
