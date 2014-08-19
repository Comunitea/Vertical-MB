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
# from openerp.tools.translate import _


class stock_task(osv.Model):
    _name = 'stock.task'
    _description = 'Warehouse task to organice products and locations'
    _order = "id desc"
    _columns = {
        'user_id': fields.many2one('res.users', 'User', required=True,
                                   readonly=True),
        'type': fields.selection([('ubication', 'Ubication',),
                                  ('reposition', 'Reposition'),
                                  ('picking', 'Picking')],
                                 'Task Type', required=True, readonly=True),
        'date_start': fields.datetime("Date Start", readonly=True,
                                      required=True),
        'duration': fields.float('Duration', readonly=True,
                                 help="Duration in Minutes"),
        'date_end': fields.datetime("Date End", readonly=True),
        'state': fields.selection([('assigned', 'Assigned'),
                                   ('canceled', 'Canceled'),
                                   ('done', 'Finished')],
                                  'State', readonly=True, required=True),
        'picking_id': fields.many2one('stock.picking', 'Picking',
                                      readonly=True),
        'wave_id': fields.many2one('stock.picking.wave', 'Wave', readonly=True)
    }
    _defaults = {
        'state': 'assigned',
    }

    def finish_task(self, cr, uid, ids, context=None):
        """
        Button method cancel a task
        """
        if context is None:
            context = {}
        for task in self.browse(cr, uid, ids, context):
            if task.picking_id:
                pick_obj = task.picking_id

                if pick_obj.state not in ['done', 'draft', 'cancel']:
                    pick_obj.approve_pack_operations()
            else:
                for picking in task.wave_id.picking_ids:
                    if picking.state not in ['done', 'draft', 'cancel']:
                        picking.approve_pack_operations()
                task.wave_id.done()
            # Write duration
            duration = datetime.now() - \
                datetime.strptime(task.date_start,
                                  DEFAULT_SERVER_DATETIME_FORMAT)
            vals = {
                'date_end': time.strftime("%Y-%m-%d %H:%M:%S"),
                'duration': duration.seconds / float(60)
            }
            task.write(vals)

        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def cancel_task(self, cr, uid, ids, context=None):
        """
        Button method cancel a task
        """
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        for task in self.browse(cr, uid, ids, context=context):
            if task.picking_id:
                task.picking_id.write({'operator_id': False,
                                       'machine_id': False})
            elif task.wave_id:
                for picking in task.wave_id.picking_ids:
                    picking.write({'operator_id': False,
                                   'machine_id': False,
                                   'wave_id': False})
                task.wave_id.refresh()
                task.wave_id.cancel_picking()

        return self.write(cr, uid, ids, {'state': 'canceled'}, context=context)

    def assign_task(self, cr, uid, ids, context=None):
        """
        Button method assign a task
        """
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'state': 'assigned'}, context=context)
