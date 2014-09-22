# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier CFolmenero Fernández$ <javier@pexego.es>
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
from openerp.osv import fields, osv
from openerp.tools.translate import _
import time


class assign_task_wzd(osv.TransientModel):
    _name = "assign.task.wzd"
    _rec_name = "operator_id"
    _columns = {
        'operator_id': fields.many2one('res.users', 'Operator',
                                       required=True,
                                       domain=[('operator', '=', 'True')]),
        'machine_id': fields.many2one('stock.machine', 'Machine',
                                      required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',
                                        required=True),
        'temp_id': fields.many2one('temp.type', 'Temperature')
    }
    _defaults = {
        'warehouse_id': lambda self, cr, uid, ctx=None:
        self.pool.get('stock.warehouse').search(cr, uid, [])[0],
    }

    def _print_report(self, cr, uid, ids, picking_id=False, wave_id=False,
                      context=None):
        if context is None:
            context = {}
        ctx = dict(context)
        if picking_id:
            ctx['active_ids'] = [picking_id]
            ctx['active_model'] = 'stock.picking'
            return self.pool.get("report").\
                get_action(cr, uid, [], 'stock.report_picking',
                           context=ctx)
        elif wave_id:
            ctx['active_model'] = 'stock.picking'
            wave = self.pool.get('stock.picking.wave').browse(cr, uid,
                                                              wave_id,
                                                              context=ctx)
            picking_ids = [picking.id for picking in wave.picking_ids]
            if not picking_ids:
                raise osv.except_osv(_('Error!'), _('Nothing to print.'))
            context['active_ids'] = picking_ids
            return self.pool.get("report").\
                get_action(cr, uid, [], 'stock.report_picking',
                           context=context)
        else:
            return

    def _change_operations_location_dest(self, cr, uid, pick_id, context=None):
        if context is None:
            context = {}
        t_pick = self.pool.get("stock.picking")
        t_pack_op = self.pool.get("stock.pack.operation")
        pick_obj = t_pick.browse(cr, uid, pick_id, context=context)
        # Writed when a ubication task is assigned
        if pick_obj.task_type == 'ubication':
            wh_obj = pick_obj.warehouse_id
            ops_ids = pick_obj.pack_operation_ids
            t_pack_op.change_location_dest_id(cr, uid, ops_ids, wh_obj,
                                              context=context)
        return True

    def _check_on_course(self, cr, uid, ids, context=None):
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        t_task = self.pool.get("stock.task")

        # Check if operator has a task on course
        domain = [
            ('user_id', '=', wzd_obj.operator_id.id),
            ('state', '=', 'assigned')
        ]
        on_course_tasks = t_task.search(cr, uid, domain, context=context)
        if on_course_tasks and not context.get('no_raise', False):
            raise osv.except_osv(_('Error!'), _('You have a task on course.'))
        return on_course_tasks

    def reprint_task(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = dict(context)
        ctx['no_raise'] = True
        on_course_task = self._check_on_course(cr, uid, ids, context=ctx)
        if not on_course_task:
            raise osv.except_osv(_('Error!'), _('No tasks to print.'))
        task = self.pool.get("stock.task").browse(cr, uid, on_course_task[0],
                                                  context=context)
        if task.wave_id:
            return self._print_report(cr, uid, ids, wave_id=task.wave_id.id,
                                      context=context)
        else:
            return self._print_report(cr, uid, ids,
                                      picking_id=task.picking_id.id,
                                      context=context)

    def get_location_task(self, cr, uid, ids, context=None):
        """
        Search pickings wich picking type equals to location task, and create
        a task of type ubication is assigned state. It writes the fields
        machine_id and operator_id of wizard in the picking.
        """
        if context is None:
            context = {}
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        t_pick = self.pool.get("stock.picking")
        t_task = self.pool.get("stock.task")

        # Check if operator has a task on course
        self._check_on_course(cr, uid, ids, context=context)

        # Get oldest internal pick in assigned state
        if not wzd_obj.warehouse_id.ubication_type_id:
            raise osv.except_osv(_('Error!'), _('No ubication type founded\
                                                 You must define the picking\
                                                 type in the warehouse.'))
        location_task_type_id = wzd_obj.warehouse_id.ubication_type_id.id
        pick_id = t_pick.search(cr, uid, [('state', '=', 'assigned'),
                                          ('picking_type_id',
                                           '=',
                                           location_task_type_id),
                                          ('operator_id', '=',
                                           False)],
                                limit=1, order="id asc",
                                context=context)
        if not pick_id:
            raise osv.except_osv(_('Error!'), _('No internal pickings to\
                                                 schedule'))

        pick = t_pick.browse(cr, uid, pick_id[0], context)
        pick.write({'operator_id': wzd_obj.operator_id.id,
                    'machine_id': wzd_obj.machine_id.id,
                    'task_type': 'ubication',
                    'warehouse_id': wzd_obj.warehouse_id.id})

        self._change_operations_location_dest(cr, uid, pick.id,
                                              context=context)

        # Create task and associate picking
        vals = {
            'user_id': wzd_obj.operator_id.id,
            'type': 'ubication',
            'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
            'picking_id': pick.id,
            'state': 'assigned',
        }
        t_task.create(cr, uid, vals, context=context)
        return self._print_report(cr, uid, ids, picking_id=pick.id,
                                  context=context)

    def cancel_task(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        t_task = self.pool.get("stock.task")
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        # Check if operator has a task on course
        domain = [
            ('user_id', '=', wzd_obj.operator_id.id),
            ('state', '=', 'assigned')
        ]
        on_course_tasks = t_task.search(cr, uid, domain, context=context,
                                        limit=1)
        if not on_course_tasks:
            raise osv.except_osv(_('Error!'), _("Imposible to cancel the task\
                                                You haven't a task assigned."))
        t_task.cancel_task(cr, uid, on_course_tasks, context=context)

    def finish_task(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        t_task = self.pool.get("stock.task")
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        # Check if operator has a task on course
        domain = [
            ('user_id', '=', wzd_obj.operator_id.id),
            ('state', '=', 'assigned')
        ]
        on_course_tasks = t_task.search(cr, uid, domain, context=context,
                                        limit=1)
        if not on_course_tasks:
            raise osv.except_osv(_('Error!'), _("Imposible to cancel the task\
                                                You haven't a task assigned."))
        t_task.finish_task(cr, uid, on_course_tasks, context=context)

    def get_reposition_task(self, cr, uid, ids, context=None):
        """
        Get reposition task assigned in reposition wizard.
        """
        if context is None:
            context = {}
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        t_pick = self.pool.get("stock.picking")
        t_task = self.pool.get("stock.task")

        # Check if operator has a task on course
        self._check_on_course(cr, uid, ids, context=context)

        # Get oldest internal pick in assigned state
        if not wzd_obj.warehouse_id.reposition_type_id:
            raise osv.except_osv(_('Error!'), _('No reposition type founded\
                                                 You must define the picking\
                                                 type in the warehouse.'))
        reposition_task_type_id = wzd_obj.warehouse_id.reposition_type_id.id
        pick_id = t_pick.search(cr, uid, [('state', '=', 'assigned'),
                                          ('picking_type_id',
                                           '=',
                                           reposition_task_type_id),
                                          ('operator_id', '=',
                                           False)],
                                limit=1, order="id asc", context=context)
        if not pick_id:
            raise osv.except_osv(_('Error!'), _('No internal reposition \
                                                 pickings to schedule'))

        pick = t_pick.browse(cr, uid, pick_id[0], context)
        pick.write({'operator_id': wzd_obj.operator_id.id,
                    'machine_id': wzd_obj.machine_id.id,
                    'warehouse_id': wzd_obj.warehouse_id.id,
                    'task_type': 'reposition'})
        # Create task and associate picking
        vals = {
            'user_id': wzd_obj.operator_id.id,
            'type': 'reposition',
            'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
            'picking_id': pick.id,
            'state': 'assigned',
        }
        t_task.create(cr, uid, vals, context=context)
        return self._print_report(cr, uid, ids, picking_id=pick.id,
                                  context=context)

    def get_picking_task(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        wave_obj = self.pool.get('stock.picking.wave')
        task_obj = self.pool.get("stock.task")
        obj = self.browse(cr, uid, ids[0], context=context)

        # Check if operator has a task on course
        self._check_on_course(cr, uid, ids, context=context)

        if not obj.temp_id:
            raise osv.except_osv(_('Error!'), _('Temperature is required to \
                                                 do a picking task'))

        to_pick_moves = move_obj.search(cr, uid, [('picking_type_id', '=',
                                                  obj.warehouse_id.
                                                  pick_type_id.id),
                                                  ('product_id.temp_type', '=',
                                                   obj.temp_id.id),
                                                  ('state', '=', 'assigned'),
                                                  ('picking_id.operator_id',
                                                   '=', False),
                                                  ('procurement_id.route_id',
                                                   '!=', False)],
                                        context=context)
        if not to_pick_moves:
            raise osv.except_osv(_('Error!'), _('Anything pending of \
                                                 picking'))
        pick_qty = 0.0
        pickings_to_wave = []
        selected_route = False
        for move in move_obj.browse(cr, uid, to_pick_moves, context=context):
            if not selected_route:
                selected_route = move.route_id.id
            if move.route_id.id != selected_route:
                continue
            new_move = False
            boxes_div = (move.product_id.supplier_un_ca or 1)
            if move.picking_id and len(move.picking_id.move_lines) > 1:
                if pick_qty >= obj.warehouse_id.max_boxes_move:
                    break
                elif (move.product_uom_qty / boxes_div) + \
                        pick_qty > obj.warehouse_id.max_boxes_move:
                    # split move
                    new_qty = obj.warehouse_id.max_boxes_move - pick_qty
                    new_qty = new_qty * boxes_div
                    new_move = move_obj.copy(cr, uid, move.id,
                                             {'product_uom_qty': new_qty,
                                              'split_from': move.id},
                                             context=context)
                    move.write({'product_uom_qty':
                                move.product_uom_qty - new_qty})
                    pick_qty = obj.warehouse_id.max_boxes_move
                else:
                    pick_qty += move.product_uom_qty / boxes_div

                # split picking
                new_pick = pick_obj.copy(cr, uid, move.picking_id.id,
                                         {'move_lines': [],
                                          'group_id': move.picking_id.
                                          group_id.id})
                if new_move:
                    move_obj.write(cr, uid, [new_move],
                                   {'picking_id': new_pick}, context=context)
                else:
                    move.write({'picking_id': new_pick})

                pickings_to_wave.append(new_pick)
            elif move.picking_id:
                pickings_to_wave.append(move.picking_id.id)

        if pickings_to_wave:
            pickings_to_wave = list(set(pickings_to_wave))
            pick_obj.write(cr, uid, pickings_to_wave,
                           {'operator_id': obj.operator_id.id,
                            'machine_id': obj.machine_id.id,
                            'warehouse_id': obj.warehouse_id.id,
                            'task_type': 'picking'},
                           context=context)
            pick_obj.prepare_package_type_operations(cr, uid, pickings_to_wave,
                                                     context=context)

            wave_id = wave_obj.create(cr, uid, {'user_id': obj.operator_id.id,
                                                'picking_ids':
                                                [(6, 0, pickings_to_wave)]},
                                      context=context)
            wave_obj.confirm_picking(cr, uid, [wave_id], context=context)
            # Create task and associate to picking wave
            vals = {
                'user_id': obj.operator_id.id,
                'type': 'picking',
                'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
                'wave_id': wave_id,
                'state': 'assigned',
            }
            task_obj.create(cr, uid, vals, context=context)
            return self._print_report(cr, uid, ids, wave_id=wave_id,
                                      context=context)

    def get_task(self, cr, uid, ids, context=None):
        try:
            return self.get_location_task(cr, uid, ids, context=context)
        except:
            pass
        try:
            return self.get_reposition_task(cr, uid, ids, context=context)
        except:
            pass
        try:
            return self.get_picking_task(cr, uid, ids, context=context)
        except Exception, e:
            raise e
