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
from openerp.osv import fields, osv
from openerp.tools.translate import _
import time
import random
from datetime import datetime, timedelta


class assign_task_wzd(osv.TransientModel):
    _name = "assign.task.wzd"
    _rec_name = "operator_id"

    def _get_next_working_date(self, cr, uid, context=None):
        """
        Returns the next working day date respect today
        """
        today = datetime.now()
        week_day = today.weekday()  # Monday 0 Sunday 6
        delta = 1
        if week_day == 4:
            delta = 3
        elif week_day == 5:
            delta = 2
        new_date = today + timedelta(days=delta or 0.0)
        date_part = datetime.strftime(new_date, "%Y-%m-%d")
        res = datetime.strptime(date_part, "%Y-%m-%d")
        return res

    _columns = {
        'operator_id': fields.many2one('res.users', 'Operator',
                                       required=True,
                                       domain=[('operator', '=', 'True')]),
        'machine_id': fields.many2one('stock.machine', 'Machine'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',
                                        required=True),
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                          domain=[('state', '=', 'active')]),
        'date_planned': fields.date('Scheduled Date', required=True,
                                    select=True,
                                    help="Date propaged to shecduled \
                                          date of related picking"),
        'location_ids': fields.many2many('stock.location',
                                         'wzd_cameras_rel',
                                         'wzd_id',
                                         'location_id',
                                         'Cameras to pick'),

    }
    _defaults = {
        'warehouse_id': lambda self, cr, uid, ctx=None:
        self.pool.get('stock.warehouse').search(cr, uid, [])[0],
        'date_planned': _get_next_working_date,
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
                get_action(cr, uid, [],
                           'midban_depot_stock.report_picking_task',
                           context=ctx)
        elif wave_id:
            ctx['active_model'] = 'stock.picking.wave'
            context['active_ids'] = [wave_id]
            return self.pool.get("report").\
                get_action(cr, uid, [],
                           'midban_depot_stock.report_picking_list',
                           context=context)
        else:
            return

    def _get_machine_from_user(self, cr, uid, ids, task_type, context=None):
        """
        Returns the property user machin for the task type, or raises and Error
        if the no machine for the task type in the user sheet.
        """
        res = False
        if context is None:
            context = {}
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        operator = wzd_obj.operator_id
        if task_type == 'ubication' and operator.location_mac_id:
            res = operator.location_mac_id.id
        elif task_type == 'reposition' and operator.reposition_mac_id:
            res = operator.reposition_mac_id.id
        elif task_type == 'picking' and operator.picking_mac_id:
            res = operator.picking_mac_id.id

        if not res:
            raise osv.except_osv(_('Error!'), _("Machine not defined either\
                                                 operator sheet or picking \
                                                 wizard"))
        return res

    def _check_on_course(self, cr, uid, ids, machine_id, context=None):
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

        if machine_id:
            domain = [
                ('machine_id', '=', machine_id),
                ('state', '=', 'assigned')
            ]
            on_course_machine = t_task.search(cr, uid, domain, context=context)
            if on_course_machine and not context.get('no_raise', False):
                raise osv.except_osv(_('Error!'), _('You have the machine\
                                                    currently assigned.'))
        return on_course_tasks

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

    def reprint_task(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = dict(context)
        ctx['no_raise'] = True
        on_course_task = self._check_on_course(cr, uid, ids, False,
                                               context=ctx)
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

# #############################################################################
# ############################## UBICATION ####################################
# #############################################################################

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
        t_ops = self.pool.get("stock.pack.operation")

        # Check if operator has a task on course
        machine_id = wzd_obj.machine_id and wzd_obj.machine_id.id or False
        if not machine_id:
            machine_id = self._get_machine_from_user(cr, uid, ids, 'ubication',
                                                     context=context)
        machine_obj = self.pool.get('stock.machine').browse(cr, uid,
                                                            machine_id)
        if machine_obj.type in ['prep_order', 'transpalet']:
            raise osv.except_osv(_('Error!'), _('Machines type %s not valid\
                                 You must select a retractil machine'))
        self._check_on_course(cr, uid, ids, machine_id, context=context)

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
        # import ipdb; ipdb.set_trace()
        domain = [('picking_id.state', '=', 'assigned'),
                  ('picking_id.picking_type_id', '=', location_task_type_id),
                  ('task_id', '=', False)]
        ops_ids = t_ops.search(cr, uid, domain, limit=1,
                               order="picking_id asc", context=context)
        if not ops_ids:
            raise osv.except_osv(_('Error'), _('No location operations to \
                                                schedule'))
        operation = t_ops.browse(cr, uid, ops_ids, context=context)
        pick = operation.picking_id
        vals = {
            'user_id': wzd_obj.operator_id.id,
            'type': 'ubication',
            'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
            # 'picking_id': pick.id,
            'state': 'assigned',
            'machine_id': machine_id
        }
        task_id = t_task.create(cr, uid, vals, context=context)
        domain = [('key', '=', 'max.loc.ops')]
        t_config = self.pool.get('ir.config_parameter')
        param_ids = t_config.search(cr, uid, domain, context=context)
        param_obj = t_config.browse(cr, uid, param_ids, context)[0]
        max_ops = int(param_obj.value)
        num_ops = len(pick.pack_operation_ids)
        if not max_ops:
            max_ops = num_ops
        assigned = 0
        for op in pick.pack_operation_ids:
            if assigned < max_ops and not op.task_id:
                op.write({'task_id': task_id})
                assigned += 1

        # pick.write({'operator_id': wzd_obj.operator_id.id,
        #             'machine_id': machine_id,
        #             'task_type': 'ubication',
        #             'warehouse_id': wzd_obj.warehouse_id.id})
        # Create task and associate picking
        # vals = {
        #     'user_id': wzd_obj.operator_id.id,
        #     'type': 'ubication',
        #     'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
        #     'picking_id': pick.id,
        #     'state': 'assigned',
        #     'machine_id': machine_id
        # }
        # t_task.create(cr, uid, vals, context=context)

        return self._print_report(cr, uid, ids, picking_id=pick.id,
                                  context=context)

# #############################################################################
# ############################## REPOSITION ###################################
# #############################################################################

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
        machine_id = wzd_obj.machine_id and wzd_obj.machine_id.id or False
        if not machine_id:
            machine_id = self._get_machine_from_user(cr, uid, ids,
                                                     'reposition',
                                                     context=context)
        machine_obj = self.pool.get('stock.machine').browse(cr, uid,
                                                            machine_id)
        if machine_obj.type in ['prep_order', 'transpalet']:
            raise osv.except_osv(_('Error!'), _('Machines type %s not valid\
                                 You must select a retractil machine'))
        self._check_on_course(cr, uid, ids, machine_id, context=context)

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
                    'machine_id': machine_id,
                    'warehouse_id': wzd_obj.warehouse_id.id,
                    'task_type': 'reposition'})
        # Create task and associate picking
        vals = {
            'user_id': wzd_obj.operator_id.id,
            'type': 'reposition',
            'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
            'picking_id': pick.id,
            'state': 'assigned',
            'machine_id': machine_id
        }
        t_task.create(cr, uid, vals, context=context)
        # wzd_obj.write({'state': 'tag'})
        # server_obj = self.pool.get('ir.actions.server')
        # context2 = {
        #     'active_id': pick.id,
        #     'active_model': 'stock.picking'
        # }
        # return server_obj.run(cr, uid, [538], context=context2)

        # return self._print_report(cr, uid, ids, picking_id=pick.id,
        #                           context=context)
        context2 = dict(context)
        context2.update({
            'active_model': 'stock.picking',
            'active_id': pick.id,
            'active_ids': [pick.id],
            'show_print_report': True,
        })
        action = {
            'name': 'Print Tags',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'create.tag.wizard',
            # 'res_id': ids[0],
            'target': 'new',
            'context': context2

        }
        return action

# #############################################################################
# ############################### PICKING #####################################
# #############################################################################
    def _get_random_route(self, cr, uid, ids, context=None):
        """
        Return a random route of any picking move
        """
        if context is None:
            context = {}
        res = False
        move_obj = self.pool.get('stock.move')
        obj = self.browse(cr, uid, ids[0], context=context)
        loc_ids = [x.id for x in obj.location_ids]
        domain = [
            ('picking_type_id', '=', obj.warehouse_id.pick_type_id.id),
            ('product_id.picking_location_id', 'child_of', loc_ids),
            ('state', '=', 'confirmed'),
            ('picking_id.operator_id', '=', False),
            ('picking_id.trans_route_id', '!=', False)
        ]
        move_ids = move_obj.search(cr, uid, domain, context=context)
        if not move_ids:
            raise osv.except_osv(_('Error!'), _('Anathing pending of picking'))
        move_objs = move_obj.browse(cr, uid, move_ids, context=context)
        routes_set = {m.picking_id.trans_route_id.id for m in move_objs}
        res = random.choice(tuple(routes_set))
        return res

    def _get_moves_from_route(self, cr, uid, ids, context=None):
        """
        Search all the assigned moves which picking has trans_route_id
        and picking location child of wizard.location_ids
        If not trans_route_id in wizard we get a random pending route
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')

        res = []
        obj = self.browse(cr, uid, ids[0], context=context)
        selected_route = obj.trans_route_id and obj.trans_route_id.id or False
        if not selected_route:
            selected_route = self._get_random_route(cr, uid, ids, context)

        date_planned = obj.date_planned
        start_date = date_planned + " 00:00:00"
        end_date = date_planned + " 23:59:59"
        loc_ids = [x.id for x in obj.location_ids]
        domain = [
            ('picking_type_id', '=', obj.warehouse_id.pick_type_id.id),
            ('product_id.picking_location_id', 'child_of', loc_ids),
            ('state', '=', 'confirmed'),
            ('picking_id.operator_id', '=', False),
            ('picking_id.trans_route_id', '=', selected_route),
            ('picking_id.min_date', '>=', start_date),
            ('picking_id.min_date', '<=', end_date),
        ]
        res = move_obj.search(cr, uid, domain, context=context)
        return (res, selected_route)

    def _get_pickings(self, cr, uid, ids, move_ids, context=None):
        """
        For all moves from a same product, get the new pickings, or the
        original picking if it only have one move.
        """
        res = set()
        if context is None:
            context = {}
        pick_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        for move in move_obj.browse(cr, uid, move_ids, context=context):
            move.action_assign()
            if move.state != 'assigned':
                continue
            if move.picking_id and len(move.picking_id.move_lines) <= 1:
                res.add(move.picking_id.id)
            else:  # Pick of move has more than one move
                new_pick = pick_obj.copy(cr, uid, move.picking_id.id,
                                         {'move_lines': [],
                                          'group_id': move.picking_id.
                                          group_id.id})
                move.write({'picking_id': new_pick})
                res.add(new_pick)
        return list(res)

    def _get_pickings_to_wave(self, cr, uid, ids, moves_by_product,
                              context=None):
        """
        @param moves_by_product: List od List: Items are
        [product_obj, [list of moves]]. Ordered by camera, Camera 1, Camera 2
        @param return: List of created picking ids to add to the wave.
        If all the moves of a same product has a volume higher than max defined
        if the wave is empty we force it, else we check for another product.
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        res = []
        max_volume = wzd_obj.warehouse_id.max_volume
        if not max_volume:
            raise osv.except_osv(_('Error'), _('No max volume defined in \
                                                warehouse'))
        for prod_moves in moves_by_product:
            product = prod_moves[0]
            move_ids = prod_moves[1]

            total_qty = 0.0
            # Can we pick all the product??
            for move in move_obj.browse(cr, uid, move_ids, context=context):
                total_qty += move.product_uom_qty
                if not product:
                    product = move.product_id

            boxes_div = product.un_ca or 1
            vol_box = product.ca_width * \
                product.ca_height * product.ca_length
            num_boxes = total_qty / boxes_div
            all_moves_vol = num_boxes * vol_box
            if all_moves_vol >= max_volume:
                if not res:  # Wave is empty so we force put in it
                    picking_ids = self._get_pickings(cr, uid, ids, move_ids,
                                                     context=context)
                    res.extend(picking_ids)
                    break
                else:  # wave is not empty so we check for another product
                    continue
            else:  # We can pick all the products
                picking_ids = self._get_pickings(cr, uid, ids, move_ids,
                                                 context=context)

                if picking_ids:
                    res.extend(picking_ids)
                else:
                    print "FAAAAALLLLLAAAAAAAR???????????????????"
        res = list(set(res))
        return res

    def get_picking_task(self, cr, uid, ids, context=None):
        """
        Assign picking task to operator. The task will be linked to a
        wave of picks.
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        wave_obj = self.pool.get('stock.picking.wave')
        task_obj = self.pool.get("stock.task")

        obj = self.browse(cr, uid, ids[0], context=context)
        # Check if operator has a task on course
        machine_id = obj.machine_id and obj.machine_id.id or False
        if not machine_id:
            machine_id = self._get_machine_from_user(cr, uid, ids, 'picking',
                                                     context=context)
        machine_obj = self.pool.get('stock.machine').browse(cr, uid,
                                                            machine_id)
        if machine_obj.type in ['retractil']:
            raise osv.except_osv(_('Error!'), _('Machines type %s not valid\
                                 You must select a machine transpalet or order\
                                 prepare'))
        self._check_on_course(cr, uid, ids, machine_id, context=context)
        if not obj.location_ids:
            raise osv.except_osv(_('Error!'), _('Locations are required to \
                                                 do a picking task'))
        to_pick_moves, selected_route = self._get_moves_from_route(cr, uid,
                                                                   ids,
                                                                   context)
        if not to_pick_moves:
            raise osv.except_osv(_('Error!'), _('Anything pending of \
                                                 picking'))
        pickings_to_wave = []
        moves_by_product = {}
        # Get the moves grouped by product
        for move in move_obj.browse(cr, uid, to_pick_moves, context=context):
            if move.product_id not in moves_by_product:
                moves_by_product[move.product_id] = [move.id]
            else:
                moves_by_product[move.product_id].append(move.id)
        # Get a order list of lists, òrdered by picking camera
        moves_by_product = sorted(moves_by_product.items(),
                                  key=lambda p:
                                  p[0].picking_location_id.get_camera())
        # Get pickings to put in a wave
        pickings_to_wave = self._get_pickings_to_wave(cr, uid, ids,
                                                      moves_by_product,
                                                      context=context)

        if pickings_to_wave:
            camera_ids = [(6, 0, [x.id for x in obj.location_ids])]
            pick_obj.write(cr, uid, pickings_to_wave,
                           {'operator_id': obj.operator_id.id,
                            'machine_id': machine_id,
                            'warehouse_id': obj.warehouse_id.id,
                            'camera_ids': camera_ids,
                            'task_type': 'picking'},
                           context=context)
            pick_obj.do_prepare_partial(cr, uid, pickings_to_wave,
                                        context=context)
            vals = {'user_id': obj.operator_id.id,
                    'camera_ids': camera_ids,
                    'trans_route_id': selected_route,
                    'warehouse_id': obj.warehouse_id.id,
                    'machine_id': obj.machine_id.id,
                    'picking_ids': [(6, 0, pickings_to_wave)]}
            wave_id = wave_obj.create(cr, uid, vals, context=context)
            # wave_obj.confirm_picking(cr, uid, [wave_id], context=context)
            # Create task and associate to picking wave
            vals = {
                'user_id': obj.operator_id.id,
                'type': 'picking',
                'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
                'wave_id': wave_id,
                'state': 'assigned',
                'machine_id': machine_id,
            }
            task_obj.create(cr, uid, vals, context=context)
            return self._print_report(cr, uid, ids, wave_id=wave_id,
                                      context=context)
        else:
            raise osv.except_osv(_('Error!'), _('No pickings to put in a \
                                                 wave'))
