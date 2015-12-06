# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Javier Colmenero Fernández<javier@comunitea.com>$
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
from openerp import models, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class ConfirmLoadWzd(models.TransientModel):
    _name = 'confirm.load.wzd'

    @api.multi
    def confirm_load(self):
        active_ids = self.env.context['active_ids']
        out_pickings = self.env['stock.picking'].browse(active_ids)
        pick_pickings = self._get_pickings_from_outs(out_pickings)
        picks_tot = pick_pickings + out_pickings
        picks_tot.write({'validated_state': 'loaded'})
         # Display the validated picks
        action_obj = self.env.ref('midban_depot_stock.action_replanning_picking_route')
        action = action_obj.read()[0]
        action['domain'] = str([('id', 'in', out_pickings._ids)])
        action['context'] = {}
        return action

    @api.multi
    def undo_load(self):
        active_ids = self.env.context['active_ids']
        out_pickings = self.env['stock.picking'].browse(active_ids)
        pick_pickings = self._get_pickings_from_outs(out_pickings, mode='undo')
        picks_tot = pick_pickings + out_pickings
        picks_tot.write({'validated_state': 'validated'})
         # Display the validated picks
        action_obj = self.env.ref('midban_depot_stock.action_delivery_man_route_sheet')
        action = action_obj.read()[0]
        action['domain'] = str([('id', 'in', out_pickings._ids)])
        action['context'] = {}
        return action
        return

    def _get_pickings_from_outs(self, out_pickings, mode='confirm'):
        wh = self.env['stock.warehouse'].search([])[0]
        res = self.env['stock.picking']
        for pick in out_pickings:
            #  if not (pick.sale_id and pick.picking_type_code == 'outgoing'):
            if not pick.picking_type_code == 'outgoing':
                raise except_orm(_('Error'),
                                 _('Picking %s must be outgoing type and  \
                                    related with a sale or \
                                    autosale' % pick.name))
            if mode == 'undo':
                if pick.validated_state == 'validated':
                    continue
                elif pick.validated_state != 'loaded':
                    raise except_orm(_('Error'),
                                     _("Picking %s should be loaded" % pick.name))
            else:
                if pick.validated_state == 'loaded':
                    continue
                if pick.validated_state != 'validated':
                    raise except_orm(_('Error'),
                                 _("Picking %s should be validated" % pick.name))
            if pick.group_id:
                domain = [('state', 'in', ['confirmed', 'assigned']),
                          ('group_id', '=', pick.group_id.id),
                          ('picking_type_id', '=', wh.pick_type_id.id)]
                pick_objs = self.env['stock.picking'].search(domain)

            # Autosale outs havent group id
            elif pick.move_lines and pick.move_lines[0].move_orig_ids:
                pick_objs = pick.move_lines[0].move_orig_ids[0].picking_id
            # pick_objs.write({'route_detail_id': pick.route_detail_id.id})
            for p in pick_objs:
                res += p

        return res