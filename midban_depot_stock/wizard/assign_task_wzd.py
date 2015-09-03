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
from openerp import api


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

    def _get_max_loc_ops(self, cr, uid, context=None):
        if context is None:
            context = {}
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'max.loc.ops', default='0')
        return int(param_value)

    def _get_min_loc_replenish(self, cr, uid, context=None):
        if context is None:
            context = {}
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'min.loc.replenish',
                                         default='1')
        return int(param_value)

    def _get_mandatory_camera(self, cr, uid, context=None):
        if context is None:
            context = {}
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'mandatory.camera',
                                         default='True')
        return True if param_value == 'True' else False

    def _get_print_report(self, cr, uid, context=None):
        if context is None:
            context = {}
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'print.report',
                                         default='True')
        return True if param_value == 'True' else False

    def operator_id_change(self, cr, uid, ids, operator_id=0, context=None):
        if context is None:
            context = {}
        res = {}
        if operator_id:
            t_tasks = self.pool.get("stock.task").search(cr, uid, [
                ('user_id', '=', operator_id),
                ('state', '=', 'assigned')])
            if len(t_tasks) == 0:
                res['have_task'] = False
                res['paused'] = False
                res['not_paused'] = False
            else:
                res['have_task'] = True
                t_tasks = self.pool.get("stock.task").search(cr, uid, [
                    ('user_id', '=', operator_id),
                    ('state', '=', 'assigned'),
                    ('paused', '=', True)])
                if len(t_tasks) > 0:
                    res['paused'] = True
                else:
                    res['paused'] = False

                t_tasks = self.pool.get("stock.task").search(cr, uid, [
                    ('user_id', '=', operator_id),
                    ('state', '=', 'assigned'),
                    ('paused', '=', False)])
                if len(t_tasks) > 0:
                    res['not_paused'] = True
                else:
                    res['not_paused'] = False

            if (res['have_task'] and not res['not_paused']) \
                    or not res['have_task']:
                res['give_me'] = False
            else:
                res['give_me'] = True
            return {'value': res}

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
                                    help="Date to search moves for picking"),
        'location_ids': fields.many2many('stock.location',
                                         'wzd_cameras_rel',
                                         'wzd_id',
                                         'location_id',
                                         'Operations by cameras',
                                         help="Select one or more camera \
                                         locations to assign operations to \
                                         task in order to get operations \
                                         whitch products are child of the \
                                         selected cameras."),
        'max_loc_ops': fields.integer('Max. nº of location operations',
                                      help='The wizard will assign this nº of \
                                      operations of an unique picking of \
                                      ubication task type'),
        'min_loc_replenish': fields.integer('Min. nº replenish location',
                                            help='the wizard will assign \
                                            operations to replenish the \
                                            defined number of locations'),
        'mandatory_camera': fields.boolean('Mandarory camera',
                                           help='If checked when you ask for a\
                                           reposition or ubication task you \
                                           muste the cameras to get operations\
                                           if not checked it will assign \
                                           operations of any camera'),
        'paused': fields.boolean(string='Tasks Paused'),
        'not_paused': fields.boolean(string='Tasks Not Paused'),
        'have_task': fields.boolean(string='Operator have task'),
        'give_me': fields.boolean(string='Give me ?'),
        'print_report': fields.boolean('Print Report', help='If checked, when \
            you get a reposition or picking task the report will be printed'),
    }
    _defaults = {
        'warehouse_id': lambda self, cr, uid, ctx=None:
        self.pool.get('stock.warehouse').search(cr, uid, [])[0],
        'date_planned': _get_next_working_date,
        'max_loc_ops': _get_max_loc_ops,
        'min_loc_replenish': _get_min_loc_replenish,
        'mandatory_camera': _get_mandatory_camera,
        'give_me': True,
        'print_report': _get_print_report,
    }

    def _print_report(self, cr, uid, ids, task_id=False, wave_id=False,
                      context=None):
        if context is None:
            context = {}
        ctx = dict(context)
        if task_id:
            ctx['active_ids'] = [task_id]
            ctx['active_model'] = 'stock.task'
            return self.pool.get("report").\
                get_action(cr, uid, [],
                           'midban_depot_stock.report_operations_list',
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
            ('state', '=', 'assigned'),
            ('paused', '=', False)
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

    def pause_run_task(self, cr, uid, ids, vals, context=None):

        if vals == 'run':
            filter = False
        else:
            filter = True

        if context is None:
            raise osv.except_osv(_('Error!'), _("Check operator:\
                                                You haven't a task assigned."))
            context = {}
        operator_id = self.browse(cr, uid, ids).operator_id.id
        t_tasks = self.pool.get("stock.task").search(cr, uid, [
            ('user_id', '=', operator_id),
            ('state', '=', 'assigned'),
            ('paused', '!=', filter)], limit=2)

        values = {'paused': filter}

        if len(t_tasks) == 1:
            t_task = self.pool.get("stock.task").browse(cr, uid, t_tasks)
            if t_task.paused != filter:
                self.pool.get("stock.task").\
                    browse(cr, uid, t_tasks).paused = filter
                t_task.write(values)

        elif len(t_tasks) == 0:
                raise osv.except_osv(_('Error!'), _("Imposible to pause tasks\
                                                    You haven't a task \
                                                    assigned/paused."))
        else:
            domain = [('name', '=', 'stock.task.view.tree.resumed')]
            res = {
                'domain': "[('user_id', '=', {0}), ('state', '=', 'assigned'),\
                            ('paused', '!=', {1})]".format(operator_id,
                                                           filter),
                'view_type': 'form',
                'view_mode': 'tree, form',
                'res_model': 'stock.task',
                'view_id':
                    self.pool.get('ir.ui.view').search(cr, uid, domain),
                'target': 'new',
                'context': context,
                'type': 'ir.actions.act_window',
            }
            return res

    def pause_task(self, cr, uid, ids, context=None):
        return self.pause_run_task(cr, uid, ids, 'pause', context=context)

    def run_task(self, cr, uid, ids, context=None):
        return self.pause_run_task(cr, uid, ids, 'run', context=context)

    def cancel_task(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        t_task = self.pool.get("stock.task")
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        # Check if operator has a task on course
        domain = [
            ('user_id', '=', wzd_obj.operator_id.id),
            ('state', '=', 'assigned'),
            ('paused', '=', False)
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
            ('state', '=', 'assigned'),
            ('paused', '=', False)
        ]
        on_course_tasks = t_task.search(cr, uid, domain, context=context,
                                        limit=1)
        if not on_course_tasks:
            raise osv.except_osv(_('Error!'), _("Imposible to cancel the task\
                                                You haven't a task assigned."))
        t_task.finish_partial_task(cr, uid, on_course_tasks, context=context)

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
                                      task_id=task.id,
                                      context=context)

    @api.multi
    def _get_task_view(self, task_id):
        self.ensure_one()
        # Open selected task in form view
        action_obj = self.env.ref('midban_depot_stock.action_stock_task')
        action = action_obj.read()[0]
        name_form = 'midban_depot_stock.stock_task_view_form'
        view_id = self.env['ir.model.data'].xmlid_to_res_id(name_form)
        action.update(views=[(view_id, 'form')], res_id=task_id)
        # import ipdb; ipdb.set_trace()
        return action


# #############################################################################
# ############################## UBICATION ####################################
# #############################################################################

    def get_run_tasks(self, cr, uid, ids, context=None):
        res = False
        operator_id = self.browse(cr, uid, ids).operator_id.id
        domain = [('user_id', '=', operator_id), ('state', '=', 'assigned'),
                  ('paused', '=', False)]
        t_task = self.pool.get("stock.task").search(cr, uid, domain)
        if t_task:
            res = True
        return res

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
        t_op = self.pool.get('stock.pack.operation')

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
        # Search withid desc because of complete the partial picking picks
        # first.
        domain = [('state', 'in', ['assigned', 'partially_available']),
                  ('picking_type_id', '=', location_task_type_id)]
        pick_ids = t_pick.search(cr, uid, domain, order="id desc",
                                 context=context)
        if not pick_ids:
            raise osv.except_osv(_('Error!'), _('No internal pickings to\
                                                 schedule'))
        camera_ids = [x.id for x in wzd_obj.location_ids]
        if not camera_ids and wzd_obj.mandatory_camera:
            raise osv.except_osv(_('Error!'),
                                 _('No cameras defined. It is configured \
                                    to get locations operations by camera\
                                    mandatorily'))
        max_ops = wzd_obj.max_loc_ops
        # if not max_ops:
        #     max_ops = 1 # ????
        op_ids = []
        pick = False  # The pick selected for operations
        for pick_id in pick_ids:  # Search operations of one UNIQUE picking
            domain = [
                ('picking_id', '=', pick_id),
                ('task_id', '=', False),
            ]
            op_ids = t_op.search(cr, uid, domain)
            if not op_ids:
                op_ids = t_op.search(cr, uid, domain)
            if op_ids:
                pick = t_pick.browse(cr, uid, pick_id, context=context)

                break

        if not op_ids:
            raise osv.except_osv(_('Error!'),
                                 _('Not found operations for picking \
                                    %s' % pick_ids))
        vals = {
            'user_id': wzd_obj.operator_id.id,
            'type': 'ubication',
            'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
            'state': 'assigned',
            'machine_id': machine_id
        }
        task_id = t_task.create(cr, uid, vals, context=context)

        assigned_ops = []
        for op in t_op.browse(cr, uid, op_ids, context=context):
            if len(assigned_ops) == max_ops:
                break
            op.assign_location()
            if wzd_obj.location_ids:
                camera_id = op.location_dest_id.get_camera()
                if not camera_id:
                    raise osv.except_osv(_('Error!'),
                                         _('Some operation of picking %s\
                                            have no a scheduled location\
                                            child of any \
                                            camera' % pick.name))
                if not (camera_id in camera_ids):
                    continue
            op.write({'task_id': task_id})
            assigned_ops.append(op)
        if pick:
            pick.write({'task_id': task_id, 'task_type': 'ubication'})
        if not assigned_ops:
            raise osv.except_osv(_('Error!'),
                                 _('Not found operations of the selected\
                                    cameras fot the picking \
                                    %s' % pick.name))
        res = {}
        if wzd_obj.print_report:
            res = self._print_report(cr, uid, ids, task_id=task_id,
                                     context=context)
        else:
            res = self._get_task_view(cr, uid, ids, task_id, context=context)
        return res

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
        t_ops = self.pool.get("stock.pack.operation")
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

        min_locs = wzd_obj.min_loc_replenish
        if not min_locs:
            min_locs = 1
        if not wzd_obj.location_ids and wzd_obj.mandatory_camera:
            raise osv.except_osv(_('Error!'), _('Cameras are required to do a \
                                 reposition task'))
        domain = [('state', '=', 'assigned'),
                  ('picking_type_id', '=', reposition_task_type_id),
                  ('operator_id', '=', False)]
        camera_ids = [x.id for x in wzd_obj.location_ids]
        if not camera_ids and wzd_obj.mandatory_camera:
            raise osv.except_osv(_('Error!'),
                                 _('No cameras defined. It is configured \
                                    to get reposition operations by camera\
                                    mandatorily'))
        if camera_ids:
            domain.append(('camera_id', 'in', camera_ids))
        pick_ids = t_pick.search(cr, uid, domain, limit=min_locs,
                                 order="id asc", context=context)
        if not pick_ids:
            raise osv.except_osv(_('Error!'), _('No internal reposition \
                                                 pickings to schedule'))
        vals = {
            'user_id': wzd_obj.operator_id.id,
            'type': 'reposition',
            'date_start': time.strftime("%Y-%m-%d %H:%M:%S"),
            'state': 'assigned',
            'machine_id': machine_id
        }
        task_id = t_task.create(cr, uid, vals, context=context)
        # vals = {
        #     'operator_id': wzd_obj.operator_id.id,
        #     'machine_id': machine_id,
        #     'warehouse_id': wzd_obj.warehouse_id.id,
        #     'task_type': 'reposition'
        # }
        # t_pick.write(cr, uid, pick_ids, vals, context=context)
        domain = [('picking_id', 'in', pick_ids), ('task_id', '=', False)]
        ops_ids = t_ops.search(cr, uid, domain, order="picking_id asc",
                               context=context)
        if not ops_ids:
            raise osv.except_osv(_('Error'), _('No reposition operations to \
                                                schedule'))
        t_ops.write(cr, uid, ops_ids, {'task_id': task_id}, context=context)

        context2 = dict(context)
        context2.update({
            'active_model': 'stock.task',
            'active_id': task_id,
            'active_ids': [task_id],
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
            ('state', 'in', ['confirmed', 'assigned']),
            ('picking_id.wave_id', '=', False),
            ('picking_id.operator_id', '=', False),
            ('picking_id.trans_route_id', '!=', False)
        ]
        move_ids = move_obj.search(cr, uid, domain, context=context)
        if not move_ids:
            raise osv.except_osv(_('Error!'), _('Anything pending of picking'))
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
            ('state', 'in', ['confirmed', 'assigned']),
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
            if move.state != 'assigned':  # Pending move to assign later.
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

        # Check if we get moves in wave by defined maximun volume or not
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'pick.by.volume',
                                         default='False')
        by_volume = param_value == 'True'
        if by_volume:
            max_volume = wzd_obj.warehouse_id.max_volume
            if not max_volume:
                raise osv.except_osv(_('Error'), _('No max volume defined in \
                                                    warehouse'))
            for prod_moves in moves_by_product:
                product = prod_moves[0]
                move_ids = prod_moves[1]

                total_qty = 0.0
                # Can we pick all the product??
                for move in move_obj.browse(cr, uid, move_ids,
                                            context=context):
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
                        picking_ids = self._get_pickings(cr, uid, ids,
                                                         move_ids,
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
        else:  # All moves will be in the picking wave
            for prod_moves in moves_by_product:
                product = prod_moves[0]
                move_ids = prod_moves[1]
                picking_ids = self._get_pickings(cr, uid, ids, move_ids,
                                                 context=context)
                if picking_ids:
                    res.extend(picking_ids)
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
            task_id = task_obj.create(cr, uid, vals, context=context)
            for pick in pick_obj.browse(cr, uid, pickings_to_wave):
                for op in pick.pack_operation_ids:
                    op.write({'task_id': task_id})
            res = {}
            if obj.print_report:
                res = self._print_report(cr, uid, ids, wave_id=wave_id,
                                         context=context)
            else:
                res = self._get_task_view(cr, uid, ids, task_id,
                                          context=context)
            return res

        else:
            raise osv.except_osv(_('Error!'), _('No pickings to put in a \
                                                 wave'))
