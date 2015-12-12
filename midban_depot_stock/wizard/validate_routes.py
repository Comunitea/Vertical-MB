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
import time
import logging
_logger = logging.getLogger(__name__)


class ValidateRoutes(models.TransientModel):

    _name = 'validate.routes'

    @api.multi
    def validate(self):
        init_t = time.time()
        active_ids = self.env.context['active_ids']
        out_pickings = self.env['stock.picking'].browse(active_ids)

        pick_pickings_tmp = self._get_pickings_from_outs(out_pickings)
        # Está bien o ordeno por la min_date del out, es decir ordeno los outs
        pick_pickings = sorted(pick_pickings_tmp, key=lambda p: p.date)
        validate_write_batch = {}
        for pick in pick_pickings:
            itera_t = time.time()
            print("----------------------------------------------------------------------------")
            print("----------------------------------------------------------------------------")
            print("SEGUIMIENTO DEL ALBARAN ", pick.name)
            print("----------------------------------------------------------------------------")
            print("----------------------------------------------------------------------------")
            if not pick.route_detail_id:
                raise except_orm(_('Error'),
                                 _('Picking %s without has not route detail \
                                    assigned' % pick.name))

            if pick.validated_state != 'no_validated' or \
                    pick.state not in ['confirmed']:
                raise except_orm(_('Error'),
                                 _('Picking %s: You can only validate unvalidated pickings' % pick.name))

            assing_tot = time.time()
            for move in pick.move_lines:
                assing_t = time.time()
                move.action_assign()
                _logger.debug("CMNT Assign time: %s", time.time() - assing_t)
                print("*****************")
                print("move ASIGNADO")
                print(time.time() - assing_t)
                print("*****************")
                # No me hace falta marcarlo como incompleto

            _logger.debug("CMNT Assign time cada completo: %s", time.time() - assing_t)
            _logger.debug("CMNT Assign time total: %s", time.time() - assing_tot)
            print("*****************")
            print("albaran ASIGNADO")
            print(time.time() - assing_tot)
            print("*****************")
            # Create as many picks as cameras involved and validate_it.
            split_t = time.time()
            picks_by_cam = self._split_pick_by_cameras(pick)
            _logger.debug("CMNT Split : %s", time.time() - split_t)
            print("*****************")
            print("albaran DIVIDIDO")
            print(time.time() - split_t)
            print("*****************")
            dev_pickings = self.get_dev_pickings_from_out(out_pickings)
            picks_tot = picks_by_cam + out_pickings + dev_pickings
            route_detail = pick.route_detail_id
            if not route_detail.id in validate_write_batch:
                detail_date = route_detail.date + " 19:00:00"
                vals2 = {'route_detail_id': route_detail.id,
                         'min_date': detail_date,
                         'validated_state': 'validated'}
                validate_write_batch[route_detail.id] = (picks_tot, vals2)

            # picks_tot.write(vals2)
            print("*****************")
            print("TIEMPO ITERACIÓN")
            print(time.time() - itera_t)
            print("*****************")
        # import ipdb; ipdb.set_trace()
        # _logger.debug("CMNT TOTAL VALIDAR: %s", time.time() - init_t)
        for det_id in validate_write_batch.keys():

            picks = validate_write_batch[det_id][0]
            vals = validate_write_batch[det_id][1]
            last_write = time.time()
            picks.write(vals)
            print("*****************")
            print("Ultima escritura")
            print(time.time() - last_write)
            print("*****************")
        print("*****************")
        print("albaran escritura fecha planificada fecha detalle y validado")
        print(time.time() - init_t)
        print("*****************")
        # Display the validated picks
        action_obj = self.env.ref('midban_depot_stock.action_replanning_picking_route')
        action = action_obj.read()[0]
        action['domain'] = str([('id', 'in', out_pickings._ids)])
        action['context'] = {}
        return action

    def get_dev_pickings_from_out(self, out_pickings):
        res = self.env['stock.picking']
        for pick in out_pickings:
            pick_objs = self.env['stock.picking']
            if pick.group_id:
                domain = [('group_id', '=', pick.group_id.id),
                        ('picking_type_id', '=', pick.picking_type_id.return_picking_type_id.id)]
                pick_objs = self.env['stock.picking'].search(domain)
            # Autosale outs havent group id
            elif pick.move_lines and pick.move_lines[0].move_orig_ids:
                pick_objs = pick.move_lines[0].move_orig_ids[0].picking_id
            for p in pick_objs:
                res += p
        return res

    def _get_pickings_from_outs(self, out_pickings):
        wh = self.env['stock.warehouse'].search([])[0]
        res = self.env['stock.picking']
        for pick in out_pickings:
            pick_objs = self.env['stock.picking']
            #  if not (pick.sale_id and pick.picking_type_code == 'outgoing'):
            if not pick.picking_type_code == 'outgoing':
                raise except_orm(_('Error'),
                                 _('Picking %s must be outgoing type and  \
                                    related with a sale or \
                                    autosale' % pick.name))

            # if not pick.route_detail_id:
            #     raise except_orm(_('Error'),
            #                      _('Picking %s without has not route detatl \
            #                        assigned' % pick.name))
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

    def _split_pick_by_cameras(self, pick):
        splited_picks = self.env['stock.picking']
        # if pick.state != 'assigned':
        #    raise except_orm(_('Error'),
        #                     _('Picking %s is not assigned' % pick.name))
        pp_t = time.time()
        pick.do_prepare_partial()
        _logger.debug("CMNT Prepare partial time: %s", time.time() - pp_t)
        moves_by_cam = {}  # Moves grouped by camera
        ops_by_cam = {}
        for op in pick.pack_operation_ids:
            camera_loc = op.location_id.get_camera()
            if camera_loc not in moves_by_cam:
                moves_by_cam[camera_loc] = self.env['stock.move']
                ops_by_cam[camera_loc] = self.env['stock.pack.operation']
            ops_by_cam[camera_loc] += op
            for x in op.linked_move_operation_ids:
                if x.move_id not in moves_by_cam[camera_loc]:
                    moves_by_cam[camera_loc] += x.move_id

        first = True
        for cam in moves_by_cam:
            if first:  # Skip first moves, we get the original picking
                first = False
                pick.camera_id = cam  # OPTIMIZAR??
                splited_picks += pick
                continue
            copy_values = {'move_lines': [],
                           'pack_operation_ids': [],
                           'route_detail_id': pick.route_detail_id.id,
                           'trans_route_id': pick.route_detail_id.route_id.id,
                           'group_id': pick.group_id.id,
                           'camera_id':cam }
            new_pick = pick.copy(copy_values)
            #print moves_by_cam[cam]
            #print ops_by_cam[cam]
            moves_by_cam[cam].with_context(do_not_propagate=True).write({'picking_id': new_pick.id})
            ops_by_cam[cam].with_context(no_recompute=True).write({'picking_id': new_pick.id})
            splited_picks += new_pick
        return splited_picks
