# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@pexego.es>
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import time
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from openerp import api
import time


class stock_task(osv.Model):
    _name = 'stock.task'
    _description = 'Warehouse task to organice products and locations'
    _order = "id desc"
    _columns = {
        'user_id': fields.many2one('res.users', 'User', required=True,
                                   readonly=False),
        'type': fields.selection([('ubication', 'Ubication',),
                                  ('reposition', 'Reposition'),
                                  ('picking', 'Picking')],
                                 'Task Type', required=True, readonly=True),
        'date_start': fields.datetime("Date Start", readonly=True,
                                      required=False),
        'duration': fields.float('Duration', readonly=True,
                                 help="Duration in Minutes"),
        'date_end': fields.datetime("Date End", readonly=True),
        'state': fields.selection([('assigned', 'Assigned'),
                                   ('canceled', 'Canceled'),
                                   ('done', 'Finished'),
                                   ('process', 'Process'),
                                   ('to_revised', 'To Revised')],
                                  'State', readonly=True, required=True),
        'picking_id': fields.many2one('stock.picking', 'Picking',
                                      readonly=True),
        'machine_id': fields.many2one('stock.machine', 'Machine',
                                      readonly=True),
        'wave_id': fields.many2one('stock.picking.wave', 'Wave',
                                   readonly=True),
        'paused': fields.boolean('Paused'),
        'operation_ids': fields.one2many('stock.pack.operation', 'task_id',
                                         'Operations', readonly=True,
                                         states={'assigned': [('readonly',
                                                               False)]}),
        'pack_ids': fields.many2many('stock.quant.package', 'task_pack_rel',
                                     'task_id', 'pack_id', string="Add packs",
                                     help="Search packs in ubication pìckings "
                                     "and adds the operation to task")
    }
    _defaults = {
        'state': 'assigned',
        'paused': False,
        'type': 'ubication',
        'date_start': time.strftime('%Y-%m-%d')
    }

    @api.one
    def finish_partial_task(self):

        if self.type != 'picking':
            pick_ids = list(set([x.picking_id.id for x in self.operation_ids]))
        else:
            pick_ids = list(set([x.id for x in self.wave_id.picking_ids]))
        # When we call button after the returned view of the wizard
        # 'active_model': 'stock.task' and we get an error with assert
        # in do_transfer method.
        # Changed it allways to stock.picking
        ctx = self._context.copy()
        ctx['active_model'] = 'stock.picking'
        ctx['active_ids'] = pick_ids
        ctx['active_id'] = len(pick_ids) == 1 and pick_ids[0] or False
        pick_t = self.env['stock.picking'].with_context(ctx)
        pick_objs = pick_t.browse(pick_ids)
        final_state = 'done'
        wave_final_state = 'done'
        if self.type == 'picking':
            filter_ids = []

            for pick in pick_objs:
                to_revised = False
                if len(pick.pack_operation_ids) == 1 and \
                        not pick.pack_operation_ids[0].to_process:
                    pick.wave_id = False
                    pick.operator_id = False
                    continue
                for op in pick.pack_operation_ids:
                    if op.to_revised and op.to_process:
                        final_state = 'to_revised'
                        wave_final_state = 'in_progress'
                if not to_revised:
                    filter_ids.append(pick.id)

            pick_objs = pick_t.browse(filter_ids)

        for pick in pick_objs:
            if pick.state not in ['done', 'draft', 'cancel']:
                pick.approve_pack_operations2(self.id)

        if self.type == 'picking':
            # self.wave_id.done()
            self.wave_id.state = wave_final_state

        duration = datetime.now() - \
            datetime.strptime(self.date_start, DEFAULT_SERVER_DATETIME_FORMAT)
        vals = {
            'date_end': time.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': duration.seconds / float(60),
            'state': final_state,
            'paused': False}
        return self.write(vals)

    @api.multi
    def cancel_task(self):
        """
        Button method cancel a task
        """
        for task in self:
            if task.operation_ids:
                op_vals = {'task_id': False}
                if task.type == 'reposition':
                    picks = self.env['stock.picking']
                    for operation in task.operation_ids:
                        if operation.picking_id not in picks:
                            picks += operation.picking_id
                    vals = {
                        'operator_id': False,
                        'machine_id': False,
                        'warehouse_id': False,
                    }
                    picks.write(vals)
                    # picks.do_unreserve()

                elif task.type == 'ubication':
                    op_vals.update(
                        {'location_dest_id':
                            self.env.ref('stock.stock_location_stock').id})

                elif task.type == 'picking' and task.wave_id:
                    for picking in task.wave_id.picking_ids:
                        picking.write({'operator_id': False,
                                       'machine_id': False,
                                       'wave_id': False})
                        # picking.do_unreserve()
                    task.wave_id.refresh()
                    task.wave_id.cancel_picking()
                task.operation_ids.write(op_vals)

        return self.write({'state': 'canceled',
                          'paused': False})

    @api.multi
    def pause_task(self):
        for task in self:
            if task.state == "assigned":
                if task.pause:
                    return self.write({'paused': True})
                else:
                    return self.write({'paused': False})

    @api.multi
    def assign_task(self):
        """
        Button method assign a task
        """
        return self.write({'state': 'assigned',
                          'paused': False})

    @api.one
    def add_loc_operation(self, pack_id):
        res = False
        wh = self.env['stock.warehouse'].search([])[0]
        wh_input_stock_loc_id = wh.wh_input_stock_loc_id #Playa
        wh_loc_stock_id = wh.lot_stock_id #Existencias
        pick_ubi_type_id = wh.ubication_type_id.id #Tarea de Ubicación
        wh_in_type_id = wh.in_type_id #Entrada
        #tenemos que mirar si es un multipack
        pack_id_ = self.env['stock.quant.package'].browse(pack_id)
        if pack_id_.parent_id:
            pack_id_ = pack_id_.parent_id

        if pack_id_.location_id.id != wh_input_stock_loc_id.id:
            #Solo ubico entradas
            return -1
        pack_id = pack_id_.id
        domain = [
            ('picking_id.picking_type_id', '=', pick_ubi_type_id),
            ('package_id', '=', pack_id),
            ('picking_id.state', 'in', ['assigned', 'partially_available'])
        ]
        op_objs = self.env['stock.pack.operation'].search(domain)
        time1 = time.time()
        if op_objs:
            op = op_objs[0]
            print u'Add_loc_operation: Pack %s Dest %s (id = %s)'%(op.package_id.name, op.location_dest_id.bcd_name, op.id)
        if not op_objs:
            print u'Add_loc_operation. y : Pack %s'%pack_id_.name
            #buscamos el id en un result package id desde recepciones
            domain = [('result_package_id', '=', pack_id), ('picking_id.picking_type_id', '=', wh_in_type_id.id)]
            op = self.env['stock.pack.operation'].search(domain, order = "id desc", limit = 1)
            if op.picking_id:
                group_id = op.picking_id.group_id
                domain = [('group_id', '=', group_id.id), ('picking_type_id', '=', pick_ubi_type_id)]
                pick_ubi = self.env['stock.picking'].search(domain)
                pick_ubi.do_prepare_partial()
                domain = [
                        ('picking_id.picking_type_id', '=', pick_ubi_type_id),
                        ('package_id', '=', pack_id),
                        ('picking_id.state', 'in', ['assigned', 'partially_available'])
                        ]
                op_objs = self.env['stock.pack.operation'].search(domain)
                if not op_objs:
                    raise except_orm(_('Error'), _('Not ubication operation mathcing \
                    with pack %s') %pack_id_.name)
            print u'Add_loc_operation para el paquete %s y la op %s(se han creado las operaciones desde albaran de entrada'%(pack_id_.name, op_objs[0].id)
        if op_objs:
            for op in op_objs:
                #Si ya tiene una distinta se mantiene
                if (op.location_dest_id.id ==  False or op.location_dest_id.id == wh_loc_stock_id.id or op.location_dest_id.id == wh_input_stock_loc_id) :#and not op.to_process:
                    op.assign_location()
                    print u'Se añadió: Pack %s Dest %s (id = %s)'%(op.package_id.name, op.location_dest_id.bcd_name, op.id)
                else:
                    print u'Se mantiene: Pack %s Dest %s (id = %s)'%(op.package_id.name, op.location_dest_id.bcd_name, op.id)

                res = op.id
            vals = {'task_id': self.id}
            op_objs.write(vals)

        print u"Tiempo empleado %s"%(time.time() - time1)       #op_objs.task_id = self.id

        return res

    @api.one
    def add_location_operations(self):
        if not self.pack_ids:
            raise except_orm(_('Error'),
                             _('No packs defined to add operations'))
        for pack in self.pack_ids:
            res = self.add_loc_operation(pack.id)
        return res
