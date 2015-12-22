# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
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
from openerp import models, fields, api
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from openerp.tools.float_utils import float_is_zero
import time
import logging
_logger = logging.getLogger(__name__)


class route_detail(models.Model):
    _name = 'route.detail'
    _inherit = 'route.detail'

    @api.multi
    def _get_pick_number(self):
        picking_obj = self.env['stock.picking']
        task_obj = self.env['stock.task']
        warehouse_id = self.env['stock.warehouse'].search([])[0]

        query_ops= """SELECT stock_picking.route_detail_id,
        stock_picking.camera_id, count(
        stock_pack_operation.to_process) as
        num,  stock_pack_operation.to_process
        FROM stock_pack_operation INNER JOIN
        stock_picking on stock_pack_operation.picking_id = stock_picking.id
        WHERE stock_picking.picking_type_id=%s  AND route_detail_id in (%s)
         GROUP BY stock_picking.route_detail_id, stock_picking.camera_id,
         stock_pack_operation.to_process ORDER BY route_detail_id, camera_id,
        to_process""" % (warehouse_id.pick_type_id.id,
                    ",".join([str(int(x.id)) for x in self]) )

        self.env.cr.execute(query_ops)
        res = self.env.cr.fetchall()

        dict_ops ={}
        for term in res:
            if not dict_ops.get(str(term[0]), False):
                dict_ops[str(term[0])] = {}
                dict_ops[str(term[0])][str(term[1])] = [0, 0]
                if term[2]:
                    dict_ops[str(term[0])][str(term[1])][0] = term[2]
                else:
                    dict_ops[str(term[0])][str(term[1])][1] = term[2]
            else:
                if not dict_ops[str(term[0])].get(str(term[1]), False):
                    dict_ops[str(term[0])][str(term[1])] = [0, 0]

                if term[2]:
                    dict_ops[str(term[0])][str(term[1])][0] = term[2]
                else:
                    dict_ops[str(term[0])][str(term[1])][1] = term[2]
        print dict_ops


        for detail in self:
            detail.warehouse_id = warehouse_id.id
            outs = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('picking_type_id', '=',
                                            warehouse_id.out_type_id.id)])

            outs_ready = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('picking_type_id', '=',
                                            warehouse_id.out_type_id.id),
                                                ('state', 'in',
                                                 ['assigned',
                                                  'partially_available'])])
            outs_done = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('picking_type_id', '=',
                                            warehouse_id.out_type_id.id),
                                                ('state', 'in',
                                                 ['done',])])
            outs_no_confirmed = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('picking_type_id', '=',
                                            warehouse_id.out_type_id.id),
                                                ('validated_state', '!=',
                                                 'loaded')])

            pickings_pending = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('picking_type_id', '=',
                                            warehouse_id.pick_type_id.id),
                                                ('state', 'in',
                                                 ['assigned',
                                                  'partially_available'])
                                                   ])
            pickings_done = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('picking_type_id', '=',
                                            warehouse_id.pick_type_id.id),
                                                ('state', 'in',
                                                 ['done',])])
            pickings_other = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('picking_type_id', '=',
                                            warehouse_id.pick_type_id.id),
                                                ])
            tasks_process = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ('state', '=',
                                            'process'),
                                                ])
            tasks_work = picking_obj.search([('route_detail_id', '=',
                                               detail.id),('state', 'in',
                                            ['assigned',])
                                           ])
            tasks_tot = picking_obj.search([('route_detail_id', '=',
                                               detail.id),
                                           ])

            detail.total_number = int(len(outs))
            detail.ready_number = int(len(outs_ready))
            detail.processed_number = int(len(outs_done))
            detail.no_confirmed_pick_number = int(len(outs_no_confirmed))
            detail.pending_pick_number = int(len(pickings_pending))
            detail.task_process = int(len(tasks_process))
            detail.task_work = int(len(tasks_work))
            detail.task_tot = int(len(tasks_tot))


            #Calculo de operaciones
            detail_ops= dict_ops.get(str(detail.id), False)
            total_ops = 0
            done_ops = 0
            pending_ops = 0
            percent_ops = 0
            if detail_ops:
                for cam in detail_ops.values():
                    print cam
                    total_ops += cam[0] + cam[1]
                    done_ops += cam[0]
                    pending_ops += cam[0]
                if total_ops > 0:
                    percent_ops = (done_ops / total_ops) * 100

            detail.total_ops = total_ops
            detail.done_ops = done_ops
            detail.pending_ops = pending_ops
            detail.percent_ops = percent_ops


    color = fields.Integer('Color')
    warehouse_id = fields.Many2one('stock.warehouse','Almacen' )
    total_number = fields.Integer("Nº de albaranes en ruta",
                                       readonly=True,
                                  compute='_get_pick_number',
                                  store=False)
    ready_number = fields.Integer("Albaranes para ser procesados",
                                           readonly=True,
                                  compute='_get_pick_number',
                                  store=False)
    processed_number = fields.Integer("Albaranes procesados",
                                           readonly=True,
                                  compute='_get_pick_number',
                                  store=False)
    pending_pick_number = fields.Integer("Picking pendiente",
                                           readonly=True,
                                  compute='_get_pick_number',
                                  store=False)

    no_confirmed_pick_number = fields.Integer("Albaranes NO confirmados",
                                           readonly=True,
                                  compute='_get_pick_number',
                                  store=False)

    total_ops = fields.Integer("Nº total de operaciones", readonly=True,
                                  compute='_get_pick_number',
                                  store=False)
    done_ops = fields.Integer("Operaciones ya realizadas",
                                        readonly=True,
                                  compute='_get_pick_number',
                                    store=False)
    task_process = fields.Integer("Tareas a revisar",
                                        readonly=True,
                                  compute='_get_pick_number',
                                    store=False)
    task_work = fields.Integer("Tareas en marcha",
                                        readonly=True,
                                  compute='_get_pick_number',
                                    store=False)
    task_total = fields.Integer("Tareas total",
                                        readonly=True,
                                  compute='_get_pick_number',
                                    store=False)

    pending_ops_ops = fields.Integer("Operaciones pendientes",
                                        readonly=True,
                                  compute='_get_pick_number',
                                    store=False)
    percent_ops = fields.Float("Ratio operacions procesadas", readonly=True,
                                  compute='_get_pick_number',
                                    store=False)
