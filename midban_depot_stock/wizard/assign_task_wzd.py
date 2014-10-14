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
        'temp_id': fields.many2one('temp.type', 'Temperature'),
        'route_id': fields.many2one('route', 'Transport Route',
                                    domain=[('state', '=', 'active')]),
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
                get_action(cr, uid, [],
                           'midban_depot_stock.report_picking_task',
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
                get_action(cr, uid, [],
                           'midban_depot_stock.report_picking_task',
                           context=context)
        else:
            return

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

        domain = [
            ('picking_id.machine_id', '=', wzd_obj.machine_id.id),
            ('state', '=', 'assigned')
        ]
        on_course_machine = t_task.search(cr, uid, domain, context=context)
        if on_course_machine and not context.get('no_raise', False):
            raise osv.except_osv(_('Error!'), _('You have the machine\
                                                 currently assigned.'))
        return on_course_tasks

    def get_task(self, cr, uid, ids, context=None):
        try:
            self.get_location_task(cr, uid, ids, context=context)
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

##############################################################################
############################### UBICATION ####################################
##############################################################################

    def _change_operations_location_dest(self, cr, uid, pick_id, context=None):
        if context is None:
            context = {}
        t_pick = self.pool.get("stock.picking")
        t_pack_op = self.pool.get("stock.pack.operation")
        pick_obj = t_pick.browse(cr, uid, pick_id, context=context)
        # Writed when a ubication task is assigned
        if pick_obj.task_type == 'ubication':
            wh_obj = pick_obj.warehouse_id
            ops_ids = [x.id for x in pick_obj.pack_operation_ids]
            t_pack_op.change_location_dest_id(cr, uid, ops_ids, wh_obj,
                                              context=context)
        return True

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

##############################################################################
############################### REPOSITION ###################################
##############################################################################

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

##############################################################################
################################ PICKING #####################################
##############################################################################

    def _get_moves_from_route(self, cr, uid, ids, context=None):
        """
        Search all the assigned moves which picking has route_id and
        temperature equals to wizard temp_id.
        If not route_id in wizard we get a random pending route
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')

        res = []
        obj = self.browse(cr, uid, ids[0], context=context)
        selected_route = obj.route_id and obj.route_id.id or False
        if not selected_route:
            raise osv.except_osv(_('Error!'), _('TODO Get random route'))
        domain = [
            ('picking_type_id', '=', obj.warehouse_id.pick_type_id.id),
            ('product_id.temp_type', '=', obj.temp_id.id),
            ('state', '=', 'assigned'),
            ('picking_id.operator_id', '=', False),
            ('picking_id.route_id', '=', selected_route)
        ]
        res = move_obj.search(cr, uid, domain, context=context)
        return res

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
            if move.picking_id and len(move.picking_id.move_lines) <= 1:
                res.add(move.picking_id.id)
            else:  # Pick of move has more than one move
                new_pick = pick_obj.copy(cr, uid, move.picking_id.id,
                                         {'move_lines': [],
                                          'group_id': move.picking_id.
                                          group_id.id})
                move.write({'picking_id': new_pick}, context=context)
                res.add(new_pick)
        return list(res)

    def _get_pickings_to_wave(self, cr, uid, ids, moves_by_product,
                              context=None):
        """
        @param moves_by_product: Dict: Keys are product_id and value is a list
                                 of moves with that products.
        @param return: List of created picking ids to add to the wave.
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
        for key in moves_by_product:
            move_ids = moves_by_product[key]
            product = False
            total_qty = 0.0
            # Can we pick all the product
            for move in move_obj.browse(cr, uid, move_ids, context=context):
                total_qty += move.product_uom_qty
                if not product:
                    product = move.product_id

            boxes_div = product.supplier_un_ca or 1
            vol_box = product.supplier_ca_width * \
                product.supplier_ca_height * product.supplier_ca_length
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
        self._check_on_course(cr, uid, ids, context=context)

        if not obj.temp_id:
            raise osv.except_osv(_('Error!'), _('Temperature is required to \
                                                 do a picking task'))

        to_pick_moves = self._get_moves_from_route(cr, uid, ids, context)
        if not to_pick_moves:
            raise osv.except_osv(_('Error!'), _('Anything pending of \
                                                 picking'))

        pickings_to_wave = []
        moves_by_product = {}
        for move in move_obj.browse(cr, uid, to_pick_moves, context=context):
            if move.product_id.id not in moves_by_product:
                moves_by_product[move.product_id.id] = [move.id]
            else:
                moves_by_product[move.product_id.id].append(move.id)

        # Get pickings to put in a wave
        pickings_to_wave = self._get_pickings_to_wave(cr, uid, ids,
                                                      moves_by_product,
                                                      context=context)

        if pickings_to_wave:
            pick_obj.write(cr, uid, pickings_to_wave,
                           {'operator_id': obj.operator_id.id,
                            'machine_id': obj.machine_id.id,
                            'warehouse_id': obj.warehouse_id.id,
                            'task_type': 'picking'},
                           context=context)
            pick_obj.do_prepare_partial(cr, uid, pickings_to_wave,
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
