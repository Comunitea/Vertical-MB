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
from openerp import models, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class ValidateRoutes(models.TransientModel):

    _name = 'validate.routes'

    @api.multi
    def validate(self):
        active_ids = self.env.context['active_ids']
        out_pickings = self.env['stock.picking'].browse(active_ids)

        pick_pickings = self._get_pickings_from_outs(out_pickings)

        unasigned_picks_lst = []
        for pick in pick_pickings:
            if not pick.route_detail_id:
                raise except_orm(_('Error'),
                                 _('Picking %s without has not route detail \
                                   assigned' % pick.name))

            # Put unassigned moves inside a new picking
            unassigned_pick = False
            for move in pick.move_lines:
                move.action_assign()
                if move.state != 'assigned':
                    if not unassigned_pick:
                        copy_values = {'move_lines': [],
                                       'pack_operation_ids': [],
                                       'validated': False,
                                       'route_detail_id': False,
                                       'group_id': pick.group_id.id}
                        unassigned_pick = pick.copy(copy_values)
                        unasigned_picks_lst.append(unassigned_pick)
                    move.picking_id = unassigned_pick.id

            # Create as many picks as cameras involved and validate_it.
            picks_by_cam = self._split_pick_by_cameras(pick)
            picks_by_cam.write({'validated': True})
            out_pickings.write({'validated': True})

            unassigned_ids = []
            if unasigned_picks_lst:
                for p in unasigned_picks_lst:
                    p.route_detail_id = False  # Its writed by write method
                    unassigned_ids.append(p.id)
                # Display the created pickings
                action_obj = self.env.ref('stock.action_picking_tree')
                action = action_obj.read()[0]
                action['domain'] = str([('id', 'in', unassigned_ids)])
                action['context'] = {}
                return action
        return

    def _get_pickings_from_outs(self, out_pickings):
        res = self.env['stock.picking']
        for pick in out_pickings:
            if not (pick.sale_id and pick.picking_type_code == 'outgoing'):
                raise except_orm(_('Error'),
                                 _('Picking %s wmust be outgoing type and  \
                                   related with a sale' % pick.name))

            if not pick.route_detail_id:
                raise except_orm(_('Error'),
                                 _('Picking %s without has not route detatl \
                                   assigned' % pick.name))
            if pick.group_id:
                domain = [('id', '!=', pick.id),
                          ('group_id', '=', pick.group_id.id),
                          ('picking_type_code', '!=', 'outgoing')]
                pick_objs = self.env['stock.picking'].search(domain)
                for p in pick_objs:
                    res += p
        return res

    def _split_pick_by_cameras(self, pick):
        splited_picks = self.env['stock.picking']
        if pick.state != 'assigned':
            raise except_orm(_('Error'),
                             _('Picking %s is not assigned' % pick.name))
        pick.do_prepare_partial()
        moves_by_cam = {}  # Moves grouped by camera
        for op in pick.pack_operation_ids:
            camera_loc = op.location_id.get_camera()
            if camera_loc not in moves_by_cam:
                moves_by_cam[camera_loc] = []
            move_objs = list(
                set([x.move_id for x in op.linked_move_operation_ids]))
            moves_by_cam[camera_loc].extend(move_objs)

        first = True

        for cam in moves_by_cam:
            if first:  # Skip first moves, we get the original picking
                first = False
                pick.camera_id = cam
                continue
            copy_values = {'move_lines': [],
                           'pack_operation_ids': [],
                           'route_detail_id': pick.route_detail_id.id,
                           'group_id': pick.group_id.id}
            new_pick = pick.copy(copy_values)
            for move in moves_by_cam[cam]:
                move.picking_id = new_pick  # Assign move to new pick
            new_pick.camera_id = cam  # Write the camera
            splited_picks += new_pick
        return splited_picks
