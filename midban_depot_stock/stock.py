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
from openerp import api, models, _, exceptions
from openerp.exceptions import except_orm
from openerp import fields as fields2
import openerp.addons.decimal_precision as dp
from lxml import etree
from openerp.exceptions import ValidationError
from datetime import datetime, date
import time
import logging
_logger = logging.getLogger(__name__)

class stock_picking(osv.Model):
    _inherit = "stock.picking"
    _order = "id desc"
    _columns = {
        'operator_id': fields.many2one('res.users', 'Operator',
                                       readonly=True, copy=False,
                                       domain=[('operator', '=', 'True')]),
        'machine_id': fields.many2one('stock.machine', 'Machine',
                                      readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse',
                                        'Moves warehouse', readonly=True),
        'user_id': fields.many2one('res.users',
                                   'Comercial', readonly=True),
        'task_type': fields.selection([('ubication', 'Ubication',),
                                       ('reposition', 'Reposition'),
                                       ('picking', 'Picking')],
                                      'Task Type', readonly=True),
        'route_detail_id': fields.many2one('route.detail', 'Detail Route',
                                           auto_join=True),
        # 'trans_route_id': fields.related('route_detail_id', 'route_id',
        #                                  string='Transport Route',
        #                                  type="many2one",
        #                                  relation="route",
        #                                  store=True,
        #                                  readonly=True,
        #                                  auto_join=True),
        'trans_route_id': fields.many2one('route', string="Route",
                                          readonly=True, auto_join=True),
        # 'orig_planned_date': fields.related('sale_id', 'date_planned',
        #                                     type="datetime", store=True,
        #                                     string='Order Planned Date',
        #                                     readonly=True),
        # 'detail_date': fields.related('route_detail_id', 'date',
        #                               string='Route Date',
        #                               type="date",
        #                               relation="route.detail",
        #                               store=True,
        #                               readonly=True),
        'camera_ids': fields.many2many('stock.location',
                                       'pick_cameras_rel',
                                       'pick_id',
                                       'location_id',
                                       'Cameras picked',
                                       readonly=True),
        'midban_operations': fields.boolean("Exist midban operation",
                                            copy=False),
        'cross_dock': fields.boolean("From Cross Dock order"),
        'out_report_ids': fields.one2many('out.picking.report', 'picking_id',
                                          'Delivery List', readonly=True),
        'camera_id': fields.many2one('stock.location', 'Affected camera',
                                     readonly=True,
                                     help='Writed only by reposition wizard\
        to get a reposition task of the selected cameras in the task wizard'),
        'order_note': fields.related('sale_id', 'note', readonly=True,
                                     type="text", string="Order Note"),
        'wave_id': fields.many2one('stock.picking.wave', 'Picking Wave',
                                   states={'done': [('readonly', True)],
                                           'cancel': [('readonly', True)]},
                                   help='Picking wave associated to this '
                                        'picking', copy=False)}


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        result = super(stock_picking, self).fields_view_get(
            view_id, view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            active_model = self.env.context.get('active_model', False)
            active_id = self.env.context.get('active_id', False)
            if not active_model or not active_id or active_model not in \
                    ['stock.picking.type', 'stock.picking']:
                act_ref = str(self.env.ref(
                    'midban_depot_stock.create_multipack_wizard_action').id)
                doc = etree.XML(result['arch'])
                button = doc.xpath("//button[@name='%s']" % act_ref)
                if button:
                    button = button[0]
                    button.getparent().remove(button)
                result['arch'] = etree.tostring(doc)
                return result
            active_record = self.env[active_model].browse(active_id)
            location_type = self.env.ref(
                'midban_depot_stock.picking_type_ubication_task')
            if active_model == 'stock.picking.type' and \
                    active_id != location_type.id or \
                    active_model == 'stock.picking' and \
                    active_record.picking_type_id.id != location_type.id:
                act_ref = str(self.env.ref(
                    'midban_depot_stock.create_multipack_wizard_action').id)
                doc = etree.XML(result['arch'])
                button = doc.xpath("//button[@name='%s']" % act_ref)
                if button:
                    button = button[0]
                    button.getparent().remove(button)
                result['arch'] = etree.tostring(doc)
        return result

    @api.multi
    def do_transfer(self):
        """
        Overwrited to add update the uos_qty of package_id and
        result_package_id
        """
        _logger.debug("CMNT do_transfer")
        init_t = time.time()
        self._regularize_move_quantities()
        _logger.debug("CMNT tiempo de _regularize_move_quantities: %s",
                      time.time() - init_t)
        init_dt = time.time()
        _logger.debug("CMNT comienza do_transfer heredado")
        res = super(stock_picking, self).do_transfer()
        _logger.debug("CMNT tiempo de do_transfers: %s",
                      time.time() - init_dt)
        # Calculate the uos_qty of package when remove qty from it
        for pick in self:
            for op in pick.pack_operation_ids:
                init_pr = time.time()
                if (op.package_id and op.product_id and op.uos_id) or \
                        (op.package_id and not op.product_id and op.uos_id
                            and op.result_package_id):
                    pack_uos_qty = 0
                    # Calcular uos_id equivalente
                    if op.uos_id.id == op.package_id.uos_id.id:
                        pack_uos_qty = op.uos_qty
                    else:  # Convert between operation unit to pack unit
                        pack_log_unit = op.product_id.\
                            get_uos_logistic_unit(op.package_id.uos_id.id)
                        conv_dic = op.product_id.\
                            get_sale_unit_conversions(op.uos_qty, op.uos_id.id)
                        pack_uos_qty = conv_dic[pack_log_unit]
                    op.package_id.uos_qty -= pack_uos_qty
                    #Si hay paquete destino
                    if op.result_package_id:
                        # Calcular uos_id equivalente
                        if op.uos_id.id == op.result_package_id.uos_id.id:
                            pack_uos_qty = op.uos_qty
                        else:  # Convert between operation unit to pack unit
                            uos_id = op.result_package_id.uos_id.id
                            pack_log_unit = op.product_id.\
                                get_uos_logistic_unit(uos_id)
                            conv_dic = op.product_id.\
                                get_sale_unit_conversions(op.uos_qty,
                                                          op.uos_id.id)
                            pack_uos_qty = conv_dic[pack_log_unit]
                        op.result_package_id.uos_qty += pack_uos_qty
                _logger.debug("CMNT tiempo de rev de cada operacion: %s",
                      time.time() - init_pr)
        _logger.debug("CMNT tiempo total _do_transfers: %s",
                      time.time() - init_t)
        return res

    @api.one
    def _regularize_move_quantities(self):
        _logger.debug("CMNT _regularize_move_quantities")
        self.recompute_remaining_qty(self)
        operations = []
        for move in self.move_lines:
            if move.product_id.is_var_coeff:
                total_operations = {'product_uom_qty': 0.0,
                                    'product_uos_qty': 0.0}
                for link in move.linked_move_operation_ids:
                    if link.operation_id.id not in operations:
                        operations.append(link.operation_id.id)
                        total_operations['product_uom_qty'] += \
                            link.operation_id.packed_qty
                        total_operations['product_uos_qty'] += \
                            link.operation_id.uos_qty
                if move.product_uom_qty < total_operations['product_uom_qty']:
                    move.product_uom_qty = total_operations['product_uom_qty']
                    move.product_uos_qty = total_operations['product_uos_qty']
                if move.product_uos_qty >= total_operations['product_uos_qty']:
                    # si tengo menos cantidad uos que la esperada.Almacena la
                    # cantidad (en Uos) que queda pendiente
                    move.wait_receipt_qty = move.product_uos_qty - \
                        total_operations['product_uos_qty']

    @api.multi
    def _get_total_operation_quantities(self):
        self.ensure_one()
        total_operations = {}
        for operation in self.pack_operation_ids:
            product_id = operation.operation_product_id.id
            if product_id not in total_operations.keys():
                total_operations[product_id] = {'uom': 0.0, 'uos': 0.0}
            total_operations[product_id]['uom'] += operation.packed_qty
            total_operations[product_id]['uos'] += operation.uos_qty
        return total_operations

    @api.one
    def _create_backorder_by_uos(self):
        backorder_moves = self.move_lines.get_backorder_moves()
        if not backorder_moves:
            return
        backorder_picking = self._get_backorder_picking()
        backorder_picking.write(
            {'move_lines': [(4, x) for x in backorder_moves._ids]})
        backorder_picking.action_confirm()

    @api.multi
    def _get_backorder_picking(self):
        self.ensure_one()
        backorder = self.search([('backorder_id', '=', self.id)])
        if not backorder:
            backorder_vals = self._get_backorder_values()
            backorder = self.copy(backorder_vals)
        return backorder

    @api.multi
    def _get_backorder_values(self):
        self.ensure_one()
        vals = {'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': self.id,
                'wave_id': False,
                'operator_id': False,
                'machine_id': False,
                'warehouse_id': False,
                'task_type': False,
                'camera_ids': False,
                '': False,
                }
        return vals

    @api.cr_uid_ids_context
    def approve_pack_operations(self, cr, uid, ids, context=None):
        """
        Aprove the pack operations, put the pick in done.
        Also calculate the operations for the next picking.
        In this moment we calculate the final location of each operation
        """
        if context is None:
            context = {}
        for pick in self.browse(cr, uid, ids, context=context):
            for op in pick.pack_operation_ids:
                op.write({
                    'qty_done': op.product_qty,
                    'processed': 'true'})
        self.do_transfer(cr, uid, ids, context=context)
        return True

    @api.one
    def delete_picking_package_operations(self):
        for op in self.pack_operation_ids:
            op.unlink()
        self.write({'midban_operations': False})

    @api.one
    def approve_pack_operations2(self, task_id):
        """
        It is only called by the finish_partial_task
        Approve only operations checked as to process and of a same task.
        Other operations will be copied to the new picking when do the partial
        transfer. If operations were checked to not process, then we don't
        assign the new operation to any task, if the operations were assigned
        to a task then we assign the task in the copied operation
        """
        init_t = time.time()
        _logger.debug("CMNT approve_pack_operations2")

        pending_ops = self.env['stock.pack.operation']
        pending_ops_values = []
        something_done = False
        init_pi = time.time()
        for op in self.pack_operation_ids:
            print u'Operacion para paquete %s'%op.package_id.name
            if not op.to_revised:
                if op.to_process and op.task_id and op.task_id.id == task_id:
                    something_done = True
                else:
                    pending_ops += op
                    op_vals = {
                        'product_id': op.product_id.id,
                        'product_uom_id': op.product_uom_id.id,
                        'product_qty': op.product_qty,
                        'package_id': op.package_id.id,
                        'lot_id': op.lot_id.id,
                        'location_id': op.location_id.id,
                        'location_dest_id': op.location_dest_id.id,
                        'result_package_id': op.result_package_id.id,
                        'date': op.date,
                        'owner_id': op.owner_id.id,
                        'uos_id': op.uos_id.id,
                        'uos_qty': op.uos_qty,
                        'to_revised': op.to_revised,
                        'to_process': op.to_process
                    }
                    pending_ops_values.append(op_vals)
            else:
                pending_ops += op
                op_vals = {
                    'product_id': op.product_id.id,
                    'product_uom_id': op.product_uom_id.id,
                    'product_qty': op.product_qty,
                    'package_id': op.package_id.id,
                    'lot_id': op.lot_id.id,
                    'location_id': op.location_id.id,
                    'location_dest_id': op.location_dest_id.id,
                    'result_package_id': op.result_package_id.id,
                    'date': op.date,
                    'owner_id': op.owner_id.id,
                    'uos_id': op.uos_id.id,
                    'uos_qty': op.uos_qty,
                    'to_revised': op.to_revised,
                    'to_process': op.to_process
                }
                pending_ops_values.append(op_vals)

        _logger.debug("CMNT tiempo prepara items : %s", time.time() - init_pi)
        if something_done:
            pending_ops.unlink()
            init_ddt = time.time()
            self.do_transfer()
            _logger.debug("CMNT tiempo do_transfer: %s", time.time() - init_ddt)

            new_pick_obj = self.search([('backorder_id', '=', self.id)])
            init_bo = time.time()
            if new_pick_obj and pending_ops_values:
                for value in pending_ops_values:
                    value['picking_id'] = new_pick_obj.id
                    self.env['stock.pack.operation'].with_context(no_recompute=True).create(value)
                _logger.debug("CMNT tiempo reasigna ops en BO: %s", time.time() - init_bo)
        else:
            #REVISAR NO LO TENGO CLARO
            for op in self.pack_operation_ids:
                if not op.to_revised:
                    op.task_id = False  # Write to be able to assign later
                #op.to_process = True  # Write to be to process by default,
            if self.wave_id:
                self.wave_id = False
        _logger.debug("CMNT tiempo total approve_pack_operations2 : %s", time.time() - init_t)
        return

    @api.onchange('route_detail_id')
    @api.multi
    def onchange_route_detail_id(self):
        """
        Try to find a route detail model of the closest day scheduled in a
        customer list of a detail model and assign it, also assign de date
        planned with the detail date
        """
        if self.route_detail_id:
            route_date = datetime.strptime(self.route_detail_id.date,
                                           '%Y-%m-%d').date()
            close_days = [wd.sequence for wd in self.partner_id.close_days]
            route_wd = route_date.weekday()
            self.min_date = self.route_detail_id.date + " 19:00:00"
            self.trans_route_id = self.trans_route_id.id
            if close_days and (route_wd+1) in close_days:
                return {
                    'warning': {'title': _("Warning"),
                                'message': _("You are assigning a route for a partner closed  day ")},
                }

    @api.multi
    def do_prepare_partial(self):
        """
        Overwrited in order to calculate the correct uos_qty in the operation.
        """
        init_t = time.time()
        res = super(stock_picking, self).do_prepare_partial()
        _logger.debug("CMNT Tiempo original do_prepare: %s ", time.time() - init_t)
        for picking in self:
            supplier_id = 0
            if picking.picking_type_code == 'incoming' and picking.purchase_id:
                supplier_id = picking.partner_id.id

            for move in picking.move_lines:
                if move.product_uos_qty and move.product_uos:
                    move_uos_qty = move.product_uos_qty
                    move_uos_id = move.product_uos.id
                    init_op = time.time()
                    operations = [x.operation_id for x in
                                  move.linked_move_operation_ids]
                    operations = list(set(operations))
                    _logger.debug("CMNT recuperacion opes: %s", time.time() - init_op)
                    for op in operations:
                        if not op.package_id.is_multiproduct:
                            prod = op.operation_product_id
                            var_weight = False
                            if supplier_id:
                                supp = prod.get_product_supp_record(supplier_id)
                            op_uos_qty = 0
                            init_op = time.time()
                            op_qty = op.product_qty
                            if not op.product_id:
                                op_qty = op.package_id.packed_qty
                            op_uos_qty = \
                                op.operation_product_id.uom_qty_to_uos_qty(op_qty,
                                                        move_uos_id,
                                                        supplier_id)
                            _logger.debug("CMNT cinv unid: %s", time.time() - init_op)
                            # Write the calculed uos qty in operation
                            init_save = time.time()
                            op.with_context(no_recompute=True).write(
                                {'uos_qty': op_uos_qty, 'uos_id':move_uos_id })
                            _logger.debug("CMNT Tiempo save op: %s", time.time() - init_save)
                            #op.uos_qty = op_uos_qty
                            #op.uos_id = move_uos_id
        _logger.debug("CMNT total do_prepare: %s", time.time() - init_t)
        return res

    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        backorder_id = super(stock_picking, self)._create_backorder(cr, uid, picking,
                                                           backorder_moves=backorder_moves,
                                                           context=context)
        if backorder_id:
            wh_id = self.pool.get('stock.warehouse').search(cr ,uid, [], context=context)[0]
            wh = self.pool.get('stock.warehouse').browse(cr, uid, wh_id, context=context)
            backorder = self.browse(cr,uid, backorder_id,context=context)
            if backorder.backorder_id.picking_type_code == 'outgoing':
                vals = {
                    'validated_state': 'no_validated'
                }
                backorder.do_unreserve()
                self.write(cr, uid, [backorder_id], vals, context=context)
            elif backorder.backorder_id.picking_type_id.id == wh.pick_type_id.id:
                val_state = 'loaded' if backorder.pack_operation_ids else 'validated'
                vals = {
                    'validated_state': val_state  # maintain detail route but no prepared to load into the gun
                }
                self.write(cr, uid, [backorder_id], vals, context=context)
        return backorder_id


        # if not backorder_moves:
        #     backorder_moves = picking.move_lines
        # backorder_move_ids = [x.id for x in backorder_moves if x.state not in ('done', 'cancel')]
        # if 'do_only_split' in context and context['do_only_split']:
        #     backorder_move_ids = [x.id for x in backorder_moves if x.id not in context.get('split', [])]
        #
        # if backorder_move_ids:
        #     backorder_id = self.copy(cr, uid, picking.id, {
        #         'name': '/',
        #         'move_lines': [],
        #         'pack_operation_ids': [],
        #         'backorder_id': picking.id,
        #     })
        #     backorder = self.browse(cr, uid, backorder_id, context=context)
        #     self.message_post(cr, uid, picking.id, body=_("Back order <em>%s</em> <b>created</b>.") % (backorder.name), context=context)
        #     move_obj = self.pool.get("stock.move")
        #     move_obj.write(cr, uid, backorder_move_ids, {'picking_id': backorder_id}, context=context)
        #
        #     if not picking.date_done:
        #         self.write(cr, uid, [picking.id], {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        #     self.action_confirm(cr, uid, [backorder_id], context=context)
        #     return backorder_id
        # return False


class StockPicking(models.Model):

    _inherit = "stock.picking"

    total_weight = fields2.Float(
        compute='_get_weight', digits_compute=dp.get_precision('Sale Price'),
        string='Total Weight', readonly=True, store=True,
        help="Calculed as the total of stock qty in moves * "
        "product gross weight")
    validated_state = fields2.Selection([('no_validated', 'Not Validated'),
                                         ('validated', 'Validated'),
                                         ('loaded', 'Load Confirmed')],'Validated State',
                                         default='no_validated',
                                         readonly=True,
                                         help="No validated is initial state, when validated "
                                        "state the stock is assigned, after review or reassign "
                                        "you can confirm the charge")
    partner_street = fields2.Char('Address', related='partner_id.street',
                                  readonly=True)
    partner_city = fields2.Char('City', related='partner_id.city',
                                readonly=True)
    partner_phone = fields2.Char('Phone', related='partner_id.phone',
                                 readonly=True)
    partner_ref = fields2.Char('Code', related='partner_id.ref', readonly=True)
    # EL campo note no le gusta nada por algun motivo
    sale_note = fields2.Text('Notes', related='sale_id.note')
    partner_id = fields2.Many2one(auto_join=True)
    init_hour = fields2.Float('From Hour', related='partner_id.times_delivery.time_start', readonly=True)
    end_hour = fields2.Float('From Hour',  related='partner_id.times_delivery.time_end', readonly=True)
    sale_id = fields2.Many2one(auto_join=True)


    # Se movió la funcionalidad al asistente de validacion de ruta
    # @api.multi
    # def write(self, vals):
    #     """
    #     Overwrited in order to write in the picking of type pick the detail
    #     route if the pick is not done.
    #     """
    #     init_t = time.time()
    #     _logger.debug("CMNT WRITE DE PICKING")
    #     for pick in self:
    #
    #         route_detail_id = False
    #         if 'route_detail_id' in vals:
    #             route_detail_id = vals['route_detail_id']
    #         if route_detail_id:
    #             t_detail = self.env['route.detail']
    #             detail_obj = t_detail.browse(route_detail_id)
    #             detail_date = detail_obj.date + " 19:00:00"
    #             # pick.min_date = detail_date
    #             # Write the route detail date in the min_date of picking
    #             vals['min_date'] = detail_date
    #
    #         # If outgoing picking write the route and the min_date in the
    #         # related picking of picking type, also the validated check
    #
    #             if pick.sale_id and pick.group_id and \
    #                     route_detail_id != pick.route_detail_id.id and \
    #                     pick.picking_type_code == 'outgoing':
    #                 domain = [('id', '!=', pick.id),
    #                           ('group_id', '=', pick.group_id.id),
    #                           ('picking_type_code', '!=', 'outgoing'),
    #                           ('state', '!=', 'done')]
    #                 pick_objs = self.search(domain)
    #                 if pick_objs:
    #                     print("PROPAAAAAAGOOOOOOOOOOOOOO")
    #                     vals2 = {'route_detail_id': route_detail_id,
    #                                  'min_date': detail_date}
    #                     pick_objs.write(vals2)
    #     res = super(StockPicking, self.with_context(tracking_disable=True)).write(vals)
    #     print("********************************************")
    #     print("********************************************")
    #     print(time.time() - init_t)
    #     print("********************************************")
    #     print("********************************************")
    #     return res

    # @api.multi
    # def write(self, vals):
    #     """
    #     Overwrited in order to write in the picking of type pick the detail
    #     route if the pick is not done.
    #     """
    #     init_t = time.time()
    #     _logger.debug("CMNT WRITE DE PICKING")
    #     vals2 = vals
    #     for pick in self:
    #
    #         route_detail_id = False
    #         if 'route_detail_id' in vals:
    #             route_detail_id = vals['route_detail_id']
    #         if route_detail_id:
    #             t_detail = self.env['route.detail']
    #             detail_obj = t_detail.browse(route_detail_id)
    #             detail_date = detail_obj.date + " 19:00:00"
    #             # pick.min_date = detail_date
    #             # Write the route detail date in the min_date of picking
    #             vals['min_date'] = detail_date
    #
    #         # If outgoing picking write the route and the min_date in the
    #         # related picking of picking type, also the validated check
    #
    #             if pick.sale_id and pick.group_id and \
    #                     route_detail_id != pick.route_detail_id.id and \
    #                     pick.picking_type_code == 'outgoing':
    #                 domain = [('id', '!=', pick.id),
    #                           ('group_id', '=', pick.group_id.id),
    #                           ('picking_type_code', '!=', 'outgoing'),
    #                           ('state', '!=', 'done')]
    #                 pick_objs = self.search(domain)
    #                 if pick_objs:
    #                     vals2 = {'route_detail_id': route_detail_id,
    #                              'min_date': detail_date}
    #                     self += pick_objs
    #                     # pick_objs.write(vals2)
    #     res = super(StockPicking, self.with_context(tracking_disable=True)).write(vals2)
    #     # print("********************************************")
    #     # print("********************************************")
    #     # print(time.time() - init_t)
    #     # print("********************************************")
    #     # print("********************************************")
    #     return res
    @api.multi
    def get_related_origin_pickings(self, check_outgoing=False):
        """
        :return: Recordset of pickings related, taked from the origin moves
        """
        res = self.env['stock.picking']
        for pick in self:
            if check_outgoing and not pick.picking_type_code == 'outgoing':
                raise except_orm(_('Error'),
                                 _('Picking %s must be outgoing type and  \
                                    related with a sale or \
                                    autosale' % pick.name))
            for move in pick.move_lines:
                for orig_move in move.move_orig_ids:
                    if orig_move.picking_id not in res:
                        res += orig_move.picking_id
        return res


    @api.multi
    def write(self, vals):
        """
        Inherit to write the route and route detail in the related, pickings
        and moves.
        """
        init_t = time.time()
        move_set = self.env['stock.move']
        detail_obj = False
        move_set = self.env['stock.move']
        route_detail_id = False
        if 'route_detail_id' in vals:
            route_detail_id = vals['route_detail_id']
        if route_detail_id:
            detail_obj =  self.env['route.detail'].browse(route_detail_id)
            detail_date = detail_obj.date + " 19:00:00"
            vals.update({
                'min_date': detail_date,
                'trans_route_id': detail_obj.route_id.id,
            })
        if vals.get('validated_state', False) or vals.get('route_detail_id', False):  #Propagate changes
            for pick in self:
                if detail_obj and pick.route_detail_id and pick.route_detail_id.id == \
                        detail_obj.id and not vals.get('validated_state', False):  # If validated state we need propagate
                    continue  # Skipe rewrite the same detail, is expensive
                for move in pick.move_lines:
                    if move not in move_set:
                        move_set += move
                    for move2 in move.move_orig_ids:
                        if move2.picking_id not in self:
                            self += move2.picking_id
                        if move2 not in move_set:
                            move_set += move2  # Add to the set the pikc
        # Write all moves related the route and the detail
        if move_set and vals.get('route_detail_id', False):  # only if route detail in vals
            move_set.write({'route_detail_id':detail_obj and detail_obj.id or False,
                            'trans_route_id:': detail_obj and detail_obj.route_id.id or False})

        # Self is the original self plus the related pickings in the move
        res = super(StockPicking,
                    self.with_context(tracking_disable=True)).write(vals)

        # ÑAPA, por algun motivo no escibe bien la ruta en el albarán de salida
        # Hay que hacerlo s veces (misterioso)
        if detail_obj:
            self[0].min_date = detail_obj.date + " 19:00:00"
        print("********************************************")
        print("TIEMPO WRITE MIDBAN DEPOT STOCK PICKING")
        print(time.time() - init_t)
        print("********************************************")
        print("********************************************")
        return res



    # DESABILITAMOS MENSAJERÍA PARA STOCK PICKING
    @api.model
    def create(self, data):
        return super(StockPicking, self.with_context(tracking_disable=True)).create(data)

    # @api.multi
    # def write(self, data):
    #     return super(StockPicking, self.with_context(tracking_disable=True)).write(data)

    @api.one
    @api.depends('move_lines.product_uom_qty', 'move_lines.product_id',
                 'move_lines.state',)
    def _get_weight(self):
        init_t = time.time()
        if self.picking_type_id.code != 'outgoing':
            self.total_weight = 0
            _logger.debug("CMNT _get_weight (picking) fast %s", time.time() - init_t)
            return
        total_weight = 0
        for move in self.move_lines:
            total_weight += move.product_id.weight * move.product_uom_qty
        self.total_weight = total_weight
        _logger.debug("CMNT _get_weight (picking) %s", time.time() - init_t)


class StockPackage(models.Model):
    _inherit = "stock.quant.package"
    _order = "id desc"

    @api.depends('quant_ids.lot_id')
    @api.one
    def _get_package_lot_id(self):
        """
        Returns lot of products inside the QUANTS of the pack.
        We not check childrens packages. # TODO??
        We assume no exist pack of diferents lots, in that case return False.
        """
        init_t = time.time()
        lot_id = False
        for quant in self.quant_ids:
            lot_id = quant.lot_id and quant.lot_id.id or False
            if lot_id != quant.lot_id.id:  # Founded diferents lots in pack
                lot_id = False
        self.packed_lot_id = lot_id
        _logger.debug("CMNT _get_package_lot_id %s", time.time() - init_t)

    @api.one
    def _get_unreserved_qty(self):
        unreserved_qty = 0.0
        for quant in self.quant_ids:
            if not quant.reservation_id:
                unreserved_qty += quant.qty
        self.unreserved_qty = unreserved_qty

    packed_lot_id = fields2.Many2one('stock.production.lot',
                                     string="Packed Lot",
                                     compute=_get_package_lot_id,
                                     readonly=True,
                                     store=True)
    unreserved_qty = fields2.Float('Unreserved Qty',
                                   compute=_get_unreserved_qty,
                                   readonly=True,
                                   digits_compute=
                                   dp.get_precision('Product Unit of Measure'))

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        Used by task view to show only packs in input location.
        Used to get only packs for a product with available min_qty give it
        in context
        """
        res = super(StockPackage, self).name_search(name, args=args,
                                                    operator=operator,
                                                    limit=limit)
        if self._context.get('incoming_loc_packages', False):
            wh = self.env['stock.warehouse'].search([])[0]
            input_loc = wh.wh_input_stock_loc_id
            args = [('location_id', '=', input_loc.id)]
            recs = self.search(args)
            res = recs.name_get()
        elif self._context.get('product_id', False):
            min_qty = self._context.get('min_qty', False)
            product_id = self._context.get('product_id', False)
            package_id = self._context.get('package_id', False)
            wh = self.env['stock.warehouse'].search([])[0]
            stock_loc = wh.lot_stock_id
            args = [('product_id', '=', product_id),
                    ('quant_ids', '!=', False),
                    ('location_id', 'child_of', [stock_loc.id])]
            if package_id:
                args.append(('id', '!=', package_id))
            recs = self.search(args)
            for p in recs:
                if min_qty and p.unreserved_qty < min_qty or not \
                        p.unreserved_qty:
                    recs -= p
            res = recs.name_get()

        return res


class stock_package(models.Model):
    _inherit = "stock.quant.package"
    _order = "id desc"

    def _get_packed_qty(self, cr, uid, ids, name, args, context=None):
        """
        Returns units qty inside the QUANTS of the pack.
        We check childrens packages.
        We assume no exist pack of diferents lots, in that case return False.
        """
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            qty = 0.0
            if pack.children_ids:
                child_res = self._get_packed_qty(cr, uid,
                                                 [x.id for x in
                                                  pack.children_ids], name,
                                                 args, context)
                qty += sum(child_res.values())
            for quant in pack.quant_ids:
                qty += quant.qty
            res[pack.id] = qty
        return res

    def _get_pack_mantles(self, cr, uid, ids, name, args, context=None):
        """
        Returns the number of mantles inside the package by getting the
        total qty inside the pack and rounding up the number of mantles.
        """
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            mantles = 0
            if pack.children_ids:
                child_res = self._get_pack_mantles(
                    cr, uid, [x.id for x in pack.children_ids], name, args,
                    context)
                mantles += sum(child_res.values())
            if pack.product_id:
                prod = pack.product_id
                mantles = prod.get_num_mantles(pack.packed_qty)
            res[pack.id] = mantles
        return res

    def _get_pack_volume(self, cr, uid, ids, name, args, context=None):
        """
        If package is in storage zone we need to calcule the pack volume
        with the wood height, in other case we get the volume by calculing
        the number of mantles in the pack ang geting the mantles height.
        """
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            quants_by_prod = {}
            # Group quants inside the package by product
            quants_by_prod = pack.get_products_quants()
            volume = 0
            if 'add_wood_height' in context:
                add_wood_height = context['add_wood_height']
            else:
                add_wood_height = \
                    True if pack.location_id.zone != 'picking' else False
            for product in quants_by_prod:
                quant_lst = quants_by_prod[product]
                qty = 0
                for quant in quant_lst:
                    qty += quant.qty

                if pack.location_id.zone == 'storage':
                    add_wood_height = True
                volume += product.get_volume_for(qty, add_wood_height)

            res[pack.id] = volume
        return res

    def _is_multiproduct_pack(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            res[pack.id] = len(pack.get_products_quants().keys()) > 1 or False
        return res

    _columns = {
        'product_id': fields.related('quant_ids', 'product_id', readonly=True,
                                     type="many2one", string="Product",
                                     relation="product.product"),
        'packed_qty': fields.function(_get_packed_qty, type="float",
                                      string="Packed qty",
                                      readonly=True,
                                      digits_compute=dp.get_precision
                                      ('Product Unit of Measure'),),
        'num_mantles': fields.function(_get_pack_mantles,
                                       type="integer",
                                       string="Nº mantles",
                                       readonly=True,),
        'volume': fields.function(_get_pack_volume, readonly=True,
                                  type="float",
                                  string="Volume",
                                  digits_compute=dp.get_precision
                                  ('Product Volume')),
        'is_multiproduct': fields.function(_is_multiproduct_pack,
                                           readonly=True,
                                           type="boolean",
                                           string="Is multiproduct"),
        'uos_qty': fields.float('S.U. qty',
                                digits_compute=
                                dp.get_precision('Product Unit of Measure')),
        'uos_id': fields.many2one('product.uom', 'Secondary unit'),
        'uom_id': fields.related('product_id', 'uom_id', type="many2one",
                                 relation="product.uom",
                                 string="Stock unit", readonly=True)}

    def get_products_quants(self, cr, uid, ids, context=None):
        """
        Returns a dictionary containing the quants for each product
        """
        _logger.debug("CMNT get_product_quants")
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            for quant in pack.quant_ids:
                product = quant.product_id
                if product not in res:
                    res[product] = [quant]
                else:
                    res[product].append(quant)
            if pack.children_ids:
                res.update(self.get_products_quants(
                    cr, uid, [x.id for x in pack.children_ids], context))
        return res

    def get_products_qtys(self, cr, uid, ids, context=None):
        """
        Returns a dictionary containing the quants for each product
        """
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            quants_by_prod = pack.get_products_quants()
            for prod in quants_by_prod:
                res[prod] = sum([x.qty for x in quants_by_prod[prod]])
        return res

    @api.multi
    def write(self, vals):
        """
        Overwrited in order to detect the case of an operation that moves a
        pack in a result package (action_done of stock.move adds parent_id)
        Instead of put ne pack_id as child of
        result_package_id in the operation we move the quants from package_id
        to result_package_id and the remove package_id.
        SO we can create a new behaivor in the operation: Move a pack inside
        other pack will not be possible, we only move the content of the first
        pack inside the second one and the firsrt is removes because is empty.
        """
        res = super(stock_package, self).write(vals)
        _logger.debug("CMNT WRITE DE package")
        for pack in self:
            if vals.get('parent_id', False):
                parent_lots = []
                parent = self.browse(vals['parent_id'])
                for pq in parent.quant_ids:
                    parent_lots.append(pq.lot_id.id)
                if parent_lots:
                    removed = False
                    for q in pack.quant_ids:
                        if q.lot_id.id in parent_lots:
                            q.package_id = vals['parent_id']
                            removed = True
                        if removed:
                            pack.parent_id = False
        return res


class stock_pack_operation(models.Model):
    _inherit = "stock.pack.operation"

    def _get_real_product(self, cr, uid, ids, name, args, context=None):
        _logger.debug("CMNT _get_real_product operation")
        if context is None:
            context = {}
        res = {}
        for ops in self.browse(cr, uid, ids, context=context):
            if ops.product_id:
                res[ops.id] = ops.product_id.id
            elif ops.lot_id:
                res[ops.id] = ops.lot_id.product_id.id
            elif ops.package_id and ops.package_id.product_id:
                res[ops.id] = ops.package_id.product_id.id
            elif ops.result_package_id and ops.result_package_id.product_id:
                res[ops.id] = ops.result_package_id.product_id.id
            else:
                res[ops.id] = False

        return res

    def _get_num_mantles(self, cr, uid, ids, name, args, context=None):
        """
        Return number of mantles of each operation. If we already have a pack
        we return the mantles number inside, else we return the mantles number
        of product_qty operation.
        We suppose to return a integer number, so we round up the number of
        mantles.
        """
        _logger.debug("CMNT _get_num_mantles operation")
        # se supone que se pasa desde log_unit a mantos, pero no vale
        # hay que cambiar para tener en cuenta desde cualquiera
        if context is None:
            context = {}
        res = {}
        for op in self.browse(cr, uid, ids, context=context):
            res[op.id] = 0

            if op.package_id:
                res[op.id] = op.package_id.num_mantles
                # If quit from a pack and put in other pack return the
                # operation num_mantles instead of the volume
                if op.result_package_id and op.product_id and op.product_qty:
                    res[op.id] = op.product_id.get_num_mantles(op.product_qty)
            else:
                res[op.id] = op.product_id.get_num_mantles(op.product_qty)

        return res

    def _get_qty_package(self, cr, uid, ids, name, args, context=None):
        """
        Get the qty inside the package or the qty going to a new package
        """
        _logger.debug("CMNT _get_qty_package operation")
        if context is None:
            context = {}
        res = {}
        for ope in self.browse(cr, uid, ids, context=context):
            res[ope.id] = 0
            if ope.package_id and not ope.product_id:
                res[ope.id] = ope.package_id.packed_qty
            elif ope.product_id:
                res[ope.id] = ope.product_qty
        return res

    _columns = {
        'operation_product_id': fields.function(_get_real_product,
                                                type="many2one",
                                                relation="product.product",
                                                readonly=True,
                                                string="Product"),
        'packed_lot_id': fields.related('package_id', 'packed_lot_id',
                                        type='many2one',
                                        relation='stock.production.lot',
                                        string='Packed Lot',
                                        readonly=True),
        'packed_qty': fields.function(_get_qty_package, type='float',
                                      string='Packed qty',
                                      digits_compute=
                                      dp.get_precision('Product Unit of Measure'),
                                      readonly=True),
        'num_mantles': fields.function(_get_num_mantles,
                                       type='integer',
                                       string='Nº Mantles',
                                       readonly=True),
        'task_id': fields.many2one('stock.task', 'In task', readonly=True),
        'to_process': fields.boolean('To process',
                                     help="When checked the operation will be\
                                     process when you finish task, else\
                                     will be unassigned"),
        # Used when aprovepackoperation2 on stock.picking, because this method
        # unlink the original operation and wee ned to remember it
        # In the scan_gun_warehouse module
        'old_id': fields.integer('Old id', readonly=True),
        'uos_qty': fields.float('UoS quantity',
                                digits_compute=
                                dp.get_precision('Product Unit of Measure')),
        'uos_id': fields.many2one('product.uom', 'Secondary unit'),
        'do_onchange': fields.boolean('Do onchange'),
        'changed': fields.boolean('Record changed'),
        'do_pack': fields.selection([('do_pack', 'Do Pack'),
                                    ('no_pack', 'No Pack')],"Pack Type")
                                    }

    _defaults = {
        'to_process': False,
        'do_onchange': True,
        'do_pack': 'do_pack'}

    def _search_closest_pick_location(self, prod_obj, free_loc_ids):
        loc_t = self.env['stock.location']
        if not free_loc_ids:
            raise exceptions.Warning(_('Error!'), _('No empty locations.'))
        if prod_obj.picking_location_id.volume_by_parent:
            free_loc_ids.append(prod_obj.picking_location_id.location_id.id)
        else:
            free_loc_ids.append(prod_obj.picking_location_id.id)
        locs = loc_t.browse(free_loc_ids)
        sorted_locs = sorted(locs, key=lambda l: l.name)
        try:
            index = sorted_locs.index(prod_obj.picking_location_id)
        except ValueError:
            index = sorted_locs.index(prod_obj.picking_location_id.location_id)
        if index == (len(sorted_locs) - 1):
            new_index = index - 1
        else:
            new_index = index + 1
        try:
            free_loc_ids.remove(prod_obj.picking_location_id.id)
        except ValueError:
            free_loc_ids.remove(prod_obj.picking_location_id.location_id.id)
        return sorted_locs[new_index]

    def _older_refernce_in_storage(self, product):
        """
        Search for quants of param product in his storage locations
        """
        _logger.debug("CMNT _older_refernce_in_storage operation")
        res = False
        t_quant = self.env['stock.quant']
        pick_loc = product.picking_location_id
        storage_loc_ids = pick_loc.get_locations_by_zone('storage')
        domain = [
            ('product_id', '=', product.id),
            ('location_id', 'in', storage_loc_ids)]
        quant_objs = t_quant.search(domain)
        net_qty = 0.0
        for quant in quant_objs:
            net_qty += quant.qty
        if quant_objs and net_qty:
            res = True
        return res

    def _is_picking_loc_available(self, product, prop_qty):
        """
        Return True whe picking is available and no older reference in storage
        """
        _logger.debug("CMNT _is_picking_loc_available operation")
        res = False

        if not product.picking_location_id:
            pick_loc = self.env.ref("stock.virtual_picking_location")
            return True

        pick_loc = product.picking_location_id
        volume = product.get_volume_for(prop_qty)
        avail, fill = pick_loc.get_available_volume_for_product(product)
        vol_aval = avail
        old_ref = self._older_refernce_in_storage(product)
        if (not old_ref and volume <= vol_aval):
            res = True
        return res

    @api.one
    def assign_location(self):
        _logger.debug("CMNT assign_location operation")
        if self.package_id.is_multiproduct:
            multipack_location = self.env['stock.location'].search([('multipack_location', '=', True)])
            if not multipack_location:
                raise exceptions.Warning(_('Location not found'),
                                         _('Impossible found the multipack'
                                           ' location'))
            self.location_dest_id = multipack_location
            return
        if self.operation_product_id:
            product = self.operation_product_id
            self.location_dest_id = product.picking_location_id or \
                self.env['stock.location'].search([('bcd_code', '=', '000000000')], limit = 1) or \
                self.env['stock.location'].search([('special_location', '=', True)], limit = 1)
            return

        self.location_dest_id = self.env['stock.location'].search([('special_location', '=', True)])
        return

        if self._is_picking_loc_available(product, self.packed_qty):
            #cambio para que si no hay, coja por defecto
            if product.picking_location_id:
                self.location_dest_id = product.picking_location_id.id
            else:
                self.location_dest_id = self.env.ref("stock.virtual_picking_location").id
        else:
            locations = product.picking_location_id.get_locations_by_zone(
                'storage')
            found = False
            while not found and locations:
                location = self._search_closest_pick_location(product,
                                                              locations)
                my_volume = product.get_volume_for(self.packed_qty)
                avail, fill = product.picking_location_id.get_available_volume_for_product(product)
                if location and avail > my_volume:
                    found = True
                else:
                    locations.remove(location.id)


            if found:
                self.location_dest_id = location
            else:
                special_location = self.env['stock.location'].search(
                    [('special_location', '=', True)])
                if not special_location:
                    raise exceptions.Warning(_('Location not found'),
                                             _('Impossible found an'
                                               ' special location'))
                self.location_dest_id = special_location

    @api.one
    def update_product_in_move(self):
        if self.product_id:
            for link_move in self.linked_move_operation_ids:
                if link_move.move_id.product_id != self.product_id:
                    link_move.move_id.product_id = self.product_id
                    self.changed = True

    @api.one
    def delete_related_quants(self):
        for link_move in self.linked_move_operation_ids:
            link_move.move_id.do_unreserve()

    def onchange_lot_id(self, cr, uid, ids, lot_id, context=None):
        if lot_id and ids:
            pack_op = self.browse(cr, uid, ids[0])
            if pack_op.lot_id and pack_op.lot_id.id != lot_id:
                return {'warning': {'title': _("Warning"),
                                    'message': _("Check the available "
                                                 "quantity of new lot.")}}
        return {}

    @api.multi
    def write(self, vals):
        """
        If we change lot_id or product_id in a create operation, we quit the
        pack in the first case and a exception will be raised in the second one
        """
                # if vals.get('lot_id', False):
        #     for op in self:
        #         if op.lot_id.id != vals['lot_id']:
        #             vals['package_id'] = False
        init_t = time.time()
        if vals.get('package_id', False):
            vals_package = self.env['stock.quant.package'].browse(vals['package_id'])


        _logger.debug("CMNT WRITE PACK operation CONTEXT: %s ", self.env.context)
        if vals.get('product_id', False):
            for op in self:
                product = op.product_id or op.package_id.product_id
                vals['product_uom_id'] = product.uom_id.id

                if not op.product_id and not vals.get('lot_id', False):
                    if vals.get('package_id', False):
                        vals['lot_id'] = self.env['stock.quant.package'].browse(vals['package_id']).packed_lot_id.id
                    elif op.package_id:
                        vals['lot_id'] = op.package_id.packed_lot_id.id

                if op.product_id.id != vals['product_id'] and op.product_id:
                    raise exceptions.Warning(_("Cannot change product once "
                                               "operation is created, delete "
                                               "this and crate another one in"
                                               " the picking."))

        #Hay que reescribir esto, lo hago en una función aparte.
        if vals.get('package_id', False) or vals.get('lot_id', False) or\
            vals.get('location_dest_id', False) or vals.get('do_pack', False):
            for op in self:
                #if op.picking_id.picking_type_id.id != 6:
                vals = op.get_result_package_id(vals)
                res = super(stock_pack_operation, op).write(vals)
                #op.write()
            return res
        else:
            return super(stock_pack_operation, self).write(vals)

    @api.multi
    def get_result_package_id(self,vals):
        init_t = time.time()#siempre que sea do_pack empaqueta (si hay) en pacquete destino
        picking_id = vals.get('picking_id', False) or self.picking_id.id
        picking = self.env['stock.picking'].browse(picking_id)
        wh = self.env['stock.warehouse'].search([])[0]
        pack_type = vals.get('do_pack', self.do_pack or 'do_pack')
        pick_types = [wh.in_type_id.id, wh.pick_type_id.id, wh.out_type_id.id, wh.reposition_type_id.id]
        #Las operaciones no internas, picks y ubicaciones se supone que no tienen result_package ...
        #REVISAR PARA REPOSICIONES

        if picking.picking_type_id.id in pick_types:
            return vals
        #vals['result_package_id'] =

        if vals.get('result_package_id', False):
            return vals

        if vals.get('location_dest_id', False):
            _logger.debug("CMNT comprobando en _get_result_package_id")
            pack_in_destination = False

            product_id = vals.get('product_id', self.product_id or False)
            lot_id = vals.get('lot_id', self.lot_id and self.lot_id.id or False)
            if not lot_id:
                lot_id = self.packed_lot_id.id or False
            if not lot_id and vals.get('package_id', False):
                lot_id = self.env['stock.quant.package'].browse(vals.get('package_id', False)).packed_lot_id.id
            if lot_id:
                new_loc = self.env['stock.location'].browse(vals['location_dest_id'])
                pack_in_destination = new_loc.get_package_of_lot(lot_id)
            #miramos que hace por según haya o no = lote en destino y
            #'pack_type' a do_pack o no_pack (empaquete o no)

            if not product_id:
                if pack_type == "do_pack":
                    if pack_in_destination:
                        vals['result_package_id'] = pack_in_destination.id
                    else:
                        if self.package_id:
                            vals['result_package_id'] = False

            if product_id:
                if pack_type == "do_pack":
                    if pack_in_destination:
                        vals['result_package_id'] = pack_in_destination.id
                    else:
                        new_package_id = self.env['stock.quant.package'].create({})
                        vals['result_package_id'] = new_package_id.id

                if pack_type == "no_pack":
                        new_package_id = self.env['stock.quant.package'].create({})
                        vals['result_package_id'] = new_package_id.id

        elif pack_type == "no_pack" and self.package_id:
             vals['result_package_id'] = False



        _logger.debug("CMNT tiempo en get_result_package_id: %s - %s ", time.time() - init_t, vals)
        return vals

    @api.model
    def create(self, vals):
        """
        If there is a pack in the location_dest_id with the same lot of
        operation lot we add the qty to this pack by setting it in
        result package id
        """
        init_t = time.time()
        _logger.debug("CMNT CREATE PACK operation")
        values_with_result_package_id = self.get_result_package_id(vals)
        op = super(stock_pack_operation, self).create(values_with_result_package_id)
        # lot_id = op.lot_id.id if op.lot_id.id else \
        #     (op.packed_lot_id.id if op.packed_lot_id.id else False)
        # if lot_id:
        #     # Reception operation, Suppliers to input location
        #     if not op.package_id and op.result_package_id:
        #         pass
        #     else:
        #         pack = op.location_dest_id.get_package_of_lot(lot_id)
        #         pack_to_create_id = vals.get('result_package_id', False)
        #         op.result_package_id = pack.id if pack else pack_to_create_id
        _logger.debug("CMNT CREATE PACK operation TIEMPO: %s", time.time() - init_t)
        return op

    @api.one
    @api.constrains('lot_id', 'product_id', 'package_id')
    def check_valid_operation(self):
        if not (self.product_id or self.package_id):
            raise ValidationError("It is not allowed operations whithout pack\
                and wothout product")

    @api.onchange('product_qty')
    def product_uos_id_onchange(self):
        """
        We change uos_qty field
        """
        var_weight = False
        product = self.product_id
        picking = self.picking_id
        supplier_id = 0
        if not product:
            return
        if picking.picking_type_code == 'incoming' and picking.purchase_id:
            supplier_id = picking.partner_id.id
        if supplier_id:
            supp = product.get_product_supp_record(supplier_id)
            if supp.is_var_coeff:
                    var_weight = True
        else:
            if product.is_var_coeff:
                var_weight = True
        if product and var_weight and self.product_uom_id.id == self.uos_id.id:
            self.do_onchange = False
            self.uos_qty = self.product_qty

        if product and not var_weight:
            if self.do_onchange:
                qty = self.product_qty
                new_uos_qty = product.uom_qty_to_uos_qty(qty, self.uos_id.id,
                                                         supplier_id)

                if new_uos_qty != self.uos_qty:
                    self.do_onchange = False
                    self.uos_qty = new_uos_qty
            else:
                self.do_onchange = True

    @api.onchange('uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the quantity field
        """
        var_weight = False
        product = self.product_id
        picking = self.picking_id
        supplier_id = 0
        if not product:
            return
        if picking.picking_type_code == 'incoming' and picking.purchase_id:
            supplier_id = picking.partner_id.id
        if supplier_id:
            supp = product.get_product_supp_record(supplier_id)
            if supp.is_var_coeff:
                    var_weight = True
        else:
            if product.is_var_coeff:
                var_weight = True
        if var_weight and self.product_uom_id == self.uos_id:
            self.do_onchange = False
            self.product_qty = self.uos_qty

        if not var_weight:
            if self.do_onchange:
                qty = self.uos_qty
                uos_id = self.uos_id.id
                new_quantity = product.uos_qty_to_uom_qty(qty, uos_id,
                                                          supplier_id)
                if new_quantity != self.product_qty:
                    self.do_onchange = False
                    self.product_qty = new_quantity
            else:
                self.do_onchange = True


class stock_warehouse(models.Model):
    _inherit = "stock.warehouse"
    _columns = {
        'ubication_type_id': fields.many2one('stock.picking.type',
                                             'Ubication Task Type'),
        'reposition_type_id': fields.many2one('stock.picking.type',
                                              'Reposition Task Type'),
        'max_volume': fields.float('Max. volume to move in picking',
                                   digits_compute=dp.get_precision
                                   ('Product Volume'))}


class stock_location(models.Model):
    _inherit = 'stock.location'

    def _get_max_per_filled(self, cr, uid, context=None):
        _logger.debug("CMNT _get_max_per_filled")
        if context is None:
            context = {}
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'max.per.filled',
                                         default='0')
        return float(param_value)

    def _get_location_volume(self, cr, uid, ids, name, args, context=None):
        _logger.debug("CMNT _get_location_volume")
        if context is None:
            context = {}
        res = {}
        for loc in self.browse(cr, uid, ids, context=context):
            res[loc.id] = {'volume': 0.0, 'real_volume': 0.0}
            max_per = loc.max_per_filled
            max_per = max_per if max_per <= 100.0 and max_per > 0.0 else 100.0
            if loc.volume_by_parent:
                par_loc = loc.location_id
                res[loc.id]['real_volume'] = \
                    (par_loc.width * par_loc.height * par_loc.length)\
                    / len(par_loc.child_ids)
                res[loc.id]['volume'] = res[loc.id]['real_volume']
                res[loc.id]['volume'] = res[loc.id]['volume'] * \
                    (max_per / 100.0)
                continue
            res[loc.id]['real_volume'] = loc.width * loc.height * loc.length
            res[loc.id]['volume'] = res[loc.id]['real_volume']
            res[loc.id]['volume'] = res[loc.id]['volume'] * (max_per / 100.0)
        return res

    def _get_quants_volume(self, cr, uid, quant_ids, context=None):
        """
        Function that return the total volume of quant_ids, gruping the
        packages in order to find the corect volume of var_palets.
        Palets or Var palets returns a volume by his number of mantles inside
        because when you quit some product from a palet, we discount the volume
        mantle by mantle.
        """
        _logger.debug("CMNT _get_quants_volume")
        t_quant = self.pool.get('stock.quant')
        t_pack = self.pool.get('stock.quant.package')
        if context is None:
            context = {}
        volume = 0.0
        pack_ids = set()

        for quant in t_quant.browse(cr, uid, quant_ids, context=context):
            if quant.package_id:
                pack_ids.add(quant.package_id.id)
            else:
                volume += quant.product_id.un_width * \
                    quant.product_id.un_height * \
                    quant.product_id.un_length * \
                    quant.qty
        pack_ids = list(pack_ids)
        for pack in t_pack.browse(cr, uid, pack_ids, context=context):
            net_qty = 0
            # Avoid negative quants
            for quant in pack.quant_ids:
                net_qty += quant.qty
            if net_qty:
                volume += pack.volume
        return volume

    def _get_available_volume(self, cr, uid, ids, name, args, context=None):
        _logger.debug("CMNT _get_available_volume")
        if context is None:
            context = {}
        res = {}
        for id in ids:
            res[id] = {'available_volume': 0.0, 'filled_percent': 0.0}
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        t_prod = self.pool.get('product.product')
        for loc in self.browse(cr, uid, ids, context=context):
            if loc.volume_by_parent:
                loc_qty = len(loc.location_id.child_ids)
                parent_volume = self._get_available_volume(
                    cr, uid, [loc.location_id.id], name, args,
                    context)[loc.location_id.id]['available_volume']
                res[loc.id]['available_volume'] = parent_volume / loc_qty
                res[loc.id]['filled_percent'] = \
                    (loc.volume - res[loc.id]['available_volume']) * 100 / \
                    loc.volume
                continue
            volume = 0.0
            quant_ids = quant_obj.search(cr, uid, [('location_id', 'child_of',
                                                    loc.id)],
                                         context=context)
            volume = self._get_quants_volume(cr, uid, quant_ids,
                                             context=context)
            domain = [
                ('location_dest_id', 'child_of', loc.id),
                ('processed', '=', 'false'),
                ('picking_id.state', 'in', ['assigned'])]
            operation_ids = ope_obj.search(cr, uid, domain, context=context)
            ops_by_pack = {}
            is_pick_zone = loc.zone == 'picking'
            # if picking location we get the volume without wood beacuse in
            # picking zone we use only one wood, and we add this volume later
            add_wood_height = False if is_pick_zone else True
            for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
                # Operation Beach to input
                if not ope.package_id and ope.result_package_id:
                    pack = ope.result_package_id
                    if pack not in ops_by_pack:
                        ops_by_pack[ope.result_package_id] = [ope]
                    else:
                        ops_by_pack[ope.result_package_id].append(ope)
                # Location task operations or reposition
                elif not ope.product_id and ope.package_id:
                    pack_obj = ope.package_id.\
                        with_context(add_wood_height=add_wood_height)
                    volume += pack_obj.volume
                # Reposition operations, remove from a pack and put in other
                elif ope.product_id and ope.package_id \
                        and ope.result_package_id:
                    volume += ope.product_id.get_volume_for(ope.product_qty)
                # Units operations, no packages
                else:
                    volume += ope.operation_product_id.un_width * \
                        ope.operation_product_id.un_height * \
                        ope.operation_product_id.un_length * \
                        ope.product_qty

            for pack in ops_by_pack:  # For multiproducts packs
                ops_lst = ops_by_pack[pack]
                sum_heights = 0
                width_wood = 0
                length_wood = 0
                wood_height = 0
                for ope in ops_lst:
                    product = ope.product_id
                    if product.pa_width > width_wood:
                        width_wood = product.pa_width
                        length_wood = product.pa_length
                        wood_height = product.palet_wood_height
                    qty = ope.product_qty
                    num_mantles = product.get_num_mantles(qty)
                    mantle_height = product.ma_height
                    sum_heights += num_mantles * mantle_height
                # If storage location add volume of wood
                if not is_pick_zone:
                    sum_heights += wood_height
                volume += width_wood * length_wood * sum_heights

            if is_pick_zone:   # Add wood volume, only one wood
                prod_id = t_prod.search(cr, uid,
                                        [('picking_location_id', '=', loc.id)],
                                        context=context, limit=1)
                if prod_id:
                    prod_obj = t_prod.browse(cr, uid, prod_id, context=context)
                    volume += prod_obj.get_wood_volume()

            res[loc.id]['available_volume'] = loc.volume - volume
            fill_per = loc.volume and volume * 100.0 / loc.volume or 0.0
            res[loc.id]['filled_percent'] = fill_per
        return res

    def _search_available_volume(self, cr, uid, obj, name, args, context=None):
        """ Function search to use available volume like a filter """
        _logger.debug("CMNT _search_available_volume")
        if context is None:
            context = {}
        sel_loc_ids = []
        volume = args and args[0][2] or False
        if args and context.get('operation', False):
            op = context['operation']
            loc_ids = obj.search(cr, uid, [], context=context)
            for loc in obj.browse(cr, uid, loc_ids, context=context):
                if op == 'equal' and loc.available_volume == volume:
                    sel_loc_ids.append(loc.id)
                elif op == 'greater'and loc.available_volume > volume:
                    sel_loc_ids.append(loc.id)
                elif op == 'less'and loc.available_volume < volume:
                    sel_loc_ids.append(loc.id)
        res = [('id', 'in', sel_loc_ids)]
        return res

    def _search_filled_percent(self, cr, uid, obj, name, args, context=None):
        """ Function search to use filled % like a filter. """
        _logger.debug("CMNT _search_available_volume")
        if context is None:
            context = {}
        sel_loc_ids = []
        percentage = args and args[0][2] or False
        if args and context.get('operation', False):
            op = context['operation']
            loc_ids = obj.search(cr, uid, [], context=context)
            for loc in obj.browse(cr, uid, loc_ids, context=context):
                if op == 'equal' and loc.filled_percent == percentage:
                    sel_loc_ids.append(loc.id)
                elif op == 'greater'and loc.filled_percent > percentage:
                    sel_loc_ids.append(loc.id)
                elif op == 'less'and loc.filled_percent < percentage:
                    sel_loc_ids.append(loc.id)
        res = [('id', 'in', sel_loc_ids)]

        return res

    def get_available_volume_for_product(self, cr, uid, ids, product,
                                         context=None):
        _logger.debug("CMNT get_available_volume_for_product")
        loc = self.browse(cr, uid, ids, context)[0]
        products = self.pool.get('product.product').search(
            cr, uid, [('picking_location_id', '=', loc.id)], context=context)
        portion_product = len(products)
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        volume = 0.0
        quant_ids = quant_obj.search(cr, uid, [('location_id', 'child_of',
                                                loc.id),
                                               ('product_id', '=',
                                                product.id)],
                                     context=context)
        volume = self.pool.get('stock.location')._get_quants_volume(
            cr, uid, quant_ids, context=context)
        domain = [
            ('location_dest_id', 'child_of', loc.id),
            ('processed', '=', 'false'),
            ('product_id', '=', product.id),
            ('picking_id.state', 'in', ['assigned'])]
        operation_ids = ope_obj.search(cr, uid, domain, context=context)
        ops_by_pack = {}
        is_pick_zone = loc.zone == 'picking'
        # if picking location we get the volume without wood beacuse in
        # picking zone we use only one wood, and we add this volume later
        add_wood_height = False if is_pick_zone else True
        for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
            # Operation Beach to input
            if not ope.package_id and ope.result_package_id:
                pack = ope.result_package_id
                if pack not in ops_by_pack:
                    ops_by_pack[ope.result_package_id] = [ope]
                else:
                    ops_by_pack[ope.result_package_id].append(ope)
            # Location task operations or reposition
            elif not ope.product_id and ope.package_id:
                pack_obj = ope.package_id.\
                    with_context(add_wood_height=add_wood_height)
                volume += pack_obj.volume
            # Reposition operations, remove from a pack and put in other
            elif ope.product_id and ope.package_id \
                    and ope.result_package_id:
                volume += ope.product_id.get_volume_for(ope.product_qty)
            # Units operations, no packages
            else:
                volume += ope.operation_product_id.un_width * \
                    ope.operation_product_id.un_height * \
                    ope.operation_product_id.un_length * \
                    ope.product_qty
        available_volume = (loc.volume / portion_product) - volume
        fill_per = loc.volume and volume * 100.0 / \
            (loc.volume / portion_product) or 0.0
        return available_volume, fill_per

    def _get_filter_percentage(self, cr, uid, ids, name, args, context=None):
        """ Function search to use filled % like a filter. """
        _logger.debug("CMNT _get_filter_percentage")
        if context is None:
            context = {}
        res = {}
        for loc in self.browse(cr, uid, ids, context=context):
            res[loc.id] = 'cualquier_cosa'
        return res

    def _search_filter_percent(self, cr, uid, obj, name, args, context=None):
        _logger.debug("CMNT _search_filter_percent")
        if context is None:
            context = {}
        sel_loc_ids = []
        percentage = args and args[0][2] or False
        if args:
            loc_ids = obj.search(cr, uid, [], context=context)
            for loc in obj.browse(cr, uid, loc_ids, context=context):
                if len(percentage.split('-')) == 2:
                    inf = int(percentage.split('-')[0])
                    sup = int(percentage.split('-')[1])
                    fill = loc.filled_percent
                    if fill > inf and fill < sup:
                        sel_loc_ids.append(loc.id)
        res = [('id', 'in', sel_loc_ids)]

        return res

    def _get_filter_available(self, cr, uid, ids, name, args, context=None):
        """ Function search to use filled % like a filter. """
        _logger.debug("CMNT _get_filter_available")
        if context is None:
            context = {}
        res = {}
        for loc in self.browse(cr, uid, ids, context=context):
            res[loc.id] = 'cualquier_cosa'
        return res

    def _search_filter_aval(self, cr, uid, obj, name, args, context=None):
        _logger.debug("CMNT _search_filter_available")
        if context is None:
            context = {}
        sel_loc_ids = []
        available = args and args[0][2] or False
        if args:
            loc_ids = obj.search(cr, uid, [], context=context)
            for loc in obj.browse(cr, uid, loc_ids, context=context):
                if len(available.split('-')) == 2:
                    inf = int(available.split('-')[0])
                    sup = int(available.split('-')[1])
                    aval = loc.available_volume
                    if aval > inf and aval < sup:
                        sel_loc_ids.append(loc.id)
        res = [('id', 'in', sel_loc_ids)]

        return res

    def _get_current_product_id(self, cr, uid, ids, name, args, context=None):
        _logger.debug("CMNT _get_current_product_id")
        if context is None:
            context = {}
        res = {}
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        for loc in self.browse(cr, uid, ids, context=context):
            res[loc.id] = False
            quant_ids = quant_obj.search(cr, uid, [('location_id', '=',
                                                    loc.id)],
                                         context=context, limit=1)
            if quant_ids:
                res[loc.id] = quant_obj.browse(cr, uid, quant_ids[0],
                                               context=context).product_id.id
            else:
                domain = [
                    ('location_dest_id', '=', loc.id),
                    ('processed', '=', 'false'),
                    ('picking_id.state', 'in', ['assigned'])]
                operation_ids = ope_obj.search(cr, uid, domain, limit=1,
                                               context=context)
                if operation_ids:
                    res[loc.id] = ope_obj.browse(cr, uid, operation_ids[0],
                                                 context=context).\
                        operation_product_id.id
        return res

    _columns = {
        'width': fields.float('Width',
                              digits_compute=dp.get_precision('Product Price')
                              ),
        'height': fields.float('Height',
                               digits_compute=dp.get_precision('Product Price')
                               ),
        'length': fields.float('Lenght',
                               digits_compute=dp.get_precision('Product Price')
                               ),
        'volume_by_parent': fields.boolean('Calculate volume by parent'
                                           ' location'),
        'multipack_location': fields.boolean(
            'Is a multipack location?',
            help='location used to locate multipacks'),
        'special_location': fields.boolean(
            'Is a special location?',
            help='location used when other locations are full'),
        'max_per_filled': fields.float('Max percentage filled',
                                       digits_compute=dp.
                                       get_precision('Product Price'),
                                       help="Default value from general \
                                       settings. Affects over location volume \
                                       that returns the specific percentage \
                                       the real"),
        'volume': fields.function(
            _get_location_volume, readonly=True, string='Volume', type="float",
            digits_compute=dp.get_precision('Product Volume'), multi='vol2'),
        'real_volume': fields.function(
            _get_location_volume, readonly=True, string='Real Volume',
            type="float",
            digits_compute=dp.get_precision('Product Volume'), multi='vol2'),
        'available_volume': fields.function(
            _get_available_volume, readonly=True, type="float",
            string="Available volume",
            digits_compute=dp.get_precision('Product Volume'),
            fnct_search=_search_available_volume, multi='mult'),
        'filter_available': fields.function(_get_filter_available,
                                            type="char",
                                            string="Available Between X-Y",
                                            fnct_search=_search_filter_aval),
        'filled_percent': fields.function(_get_available_volume, type="float",
                                          string="Filled %",
                                          digits_compute=dp.get_precision
                                          ('Product Price'),
                                          fnct_search=_search_filled_percent,
                                          multi='mult'),
        'filter_percent': fields.function(_get_filter_percentage,
                                          type="char",
                                          string="Filled Between X-Y",
                                          fnct_search=_search_filter_percent),
        'current_product_id': fields.function(_get_current_product_id,
                                              string="Product",
                                              readonly=True,
                                              type="many2one",
                                              relation="product.product"),
        'temp_type_id': fields.many2one('temp.type', 'Temperature Type'),
        'camera': fields.boolean('Picking Camera',
                                 help="If True we can do picking of "
                                 "this location and childrens"),
        'zone': fields.selection([('storage', 'Storage Zone'),
                                  ('picking', 'Picking Zone')],
                                 'Location Zone'),
        # Used in set_order_location_tour module, view defined in that module
        'order_seq': fields.char('Sequence order'),
    }

    _defaults = {
        'sequence': 0,
        'max_per_filled': _get_max_per_filled,
    }

    def get_camera(self, cr, uid, ids, context=None):
        """
        Get the first parent location marked as camera.
        """
        init_t = time.time()
        res = False
        if ids:
            loc_id = ids[0]
            loc = self.browse(cr, uid, loc_id, context=context)
            while not res and loc.location_id:
                if loc.location_id.camera:
                    res = loc.location_id.id
                else:
                    loc = loc.location_id
        _logger.debug("CMNT tiempo get_camera %s", time.time()-init_t)
        return res

    def get_locations_by_zone(self, cr, uid, ids, zone, add_domain=False,
                              context=None):
        """
        Get the camera from the loc_id and get the children locations of
        specified zone ('storage', 'picking')
        """
        _logger.debug("CMNT get_locations_by_zone")

        locations = []
        loc_id = ids[0]
        if context is None:
            context = {'operation': 'greater'}
        ctx = context.copy()
        if zone not in ['picking', 'storage']:
            raise exceptions.Warning(_('Error!'), _('Zone not exist.'))

        loc_camera_id = self.get_camera(cr, uid, [loc_id], context=context)
        if loc_camera_id:
            domain = [('location_id', 'child_of', [loc_camera_id]),
                      ('usage', '=', 'internal'),
                      ('zone', '=', zone)]
            if add_domain:
                ctx.update({'operation': 'greater'})
                domain.extend(add_domain)
            locations = self.search(cr, uid, domain, context=ctx)
        return locations

    def get_general_zone(self, cr, uid, ids, zone, context=None):
        """
        Get the first gereal location marked as zone (picking or storage)
        for a child location.
        """
        init_t = time.time()
        loc_id = False
        loc_id = ids[0]
        if context is None:
            context = {}
        if zone not in ['picking', 'storage']:
            raise exceptions.Warning(_('Error!'),
                                     _('Zone %s not exist.') % zone)
        loc_camera_id = self.get_camera(cr, uid, [loc_id], context=context)
        if loc_camera_id:
            domain = [('location_id', '=', loc_camera_id),
                      ('zone', '=', zone)]
            locations = self.search(cr, uid, domain, context=context)
            loc_id = locations and locations[0] or False
        if not loc_id:
            cam = self.browse(cr, uid, loc_camera_id, context).name
            raise exceptions.Warning(_('Error!'), _('No general %s location \
                                                 founded in camera %s.') %
                                     (zone, cam))
        _logger.debug("CMNT _get_general_zone time: %s", time.time() - init_t)
        return loc_id

    def on_change_parent_location(self, cr, uid, ids, loc_id, context=None):
        """
        If field zoned is setted in parent location get it in the child
        location to.
        """
        res = {'value': {}}
        if loc_id:
            loc = self.browse(cr, uid, loc_id, context=context)
            res['value'].update({'zone': loc.zone or False})
            res['value'].update({'temp_type_id': loc.temp_type_id and
                                loc.temp_type_id.id or False})
        return res

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only location of a unique product
            if search_product_id is in context."""
        init_t = time.time()
        if context is None:
            context = {}
        quant_t = self.pool.get("stock.quant")
        if context.get('search_product_id', False):
            args = []
            product_id = context['search_product_id']
            domain = [('product_id', '=', product_id)]
            quant_ids = quant_t.search(cr, uid, domain, context=context)
            loc_ids = set()
            for quant in quant_t.browse(cr, uid, quant_ids, context=context):
                loc_ids.add(quant.location_id.id)
            loc_ids = list(loc_ids)
            args.append(['id', 'in', loc_ids])
        res = super(stock_location, self).search(cr, uid, args,
                                                  offset=offset,
                                                  limit=limit,
                                                  order=order,
                                                  context=context,
                                                  count=count)
        _logger.debug("CMNT SEARCH de ubicaciones tiempo: %s ", time.time() - init_t)
        return res

    def name_search(self, cr, uid, name,
                    args=None, operator='ilike', context=None, limit=80):
        """
        Redefine the search to search by company name.
        """
        _logger.debug("CMNT NAME_SEARCH de ubicaciones")
        if context.get('search_product_id', False):
            loc_ids = self.search(cr, uid, args, context=context)
            args = [('id', 'in', loc_ids)]
        res = super(stock_location, self).name_search(cr, uid, name, args=args,
                                                      operator=operator,
                                                      limit=limit)
        return res

    @api.multi
    def replenish_picking_location(self):
        """
        Try to get a reposition Picking calling the reposition wizard with
        the unique location passed
        """
        res = {}
        vals = {'capacity': 95.0,
                'limit': 100.0,
                'warehouse_id': self.get_warehouse(self),
                'specific_locations': True,
                'selected_loc_ids': [(6, 0, [self.id])]}
        repo_wzd = self.env['reposition.wizard'].create(vals)
        res = repo_wzd.get_reposition_list()
        return res

    @api.multi
    def get_package_of_lot(self, lot_id):
        """
        Search packs in the location, if there is a pack of a lot_id
        we returne it
        """
        packs = False
        for loc in self:
            domain = [('location_id', '=', loc.id),
                      ('packed_lot_id', '=', lot_id)]
            packs = self.env['stock.quant.package'].search(domain)
        return packs and packs[0] or False


class stock_move(models.Model):
    _inherit = "stock.move"

    _columns = {
        # 'trans_route_id': fields.related('procurement_id', 'trans_route_id',
        #                                  readonly=True,
        #                                  string='Transport Route',
        #                                  relation="route",
        #                                  type="many2one"),
        # 'route_detail_id': fields.related('procurement_id', 'route_detail_id',
        #                                   readonly=True,
        #                                   string='Detail Route',
        #                                   relation="route.detail",
        #                                   type="many2one"),
        'route_detail_id': fields.many2one('route.detail', 'Detail Route',
                                           auto_join=True),
        'trans_route_id': fields.many2one('route', string="Route",
                                          readonly=True, auto_join=True),
        'orig_op': fields.many2one('stock.pack.operation', 'op'),
        'wait_receipt_qty': fields.float('Quantity pending receipt')}

    def _prepare_procurement_from_move(self, cr, uid, move, context=None):
        res = super(stock_move, self).\
            _prepare_procurement_from_move(cr, uid, move, context=context)
        route_detail = move.route_detail_id and move.route_detail_id or \
            False
        if route_detail:
            res['route_detail_id'] = route_detail.id
            res['trans_route_id'] = route_detail.route_id.id
        return res

    def _get_propagated_change_dict(self, cr, uid, vals, context=None):
        propagated_changes_dict = super(stock_move, self)._get_propagated_change_dict(cr, uid, vals,
                                            context=context)
        #CMNT propagation of quantity uos change. PATCH FOR PERFORMANCE
        if vals.get('product_uos_qty'):
            propagated_changes_dict['product_uos_qty'] = \
                vals['product_uos_qty']
        if vals.get('product_uos_id'):
            propagated_changes_dict['product_uos_id'] = \
                    vals['product_uos_id']
        return propagated_changes_dict

    def _prepare_picking_assign(self, cr, uid, move, context=None):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        res = super(stock_move, self)._prepare_picking_assign(cr, uid, move,
                                                              context=context)
        res.update({'route_detail_id': move.route_detail_id.id,
                    'trans_route_id': move.trans_route_id.id})
        return res

    # def write(self, cr, uid, ids, vals, context=None):
    #     if context is None:
    #         context = {}
    #     # TODO: se hace asi?
    #     _logger.debug("CMNT WRITE del stock.move %s - %s", vals, context)
    #     init_t = time.time()
    #     res = super(stock_move, self).write(cr, uid, ids, vals,
    #                                         context=context)
    #     _logger.debug("CMNT stock.move tiempo write original: %s",
    #                  time.time() - init_t)
    #     # para arrastrar la ruta al albaran desde la venta
    #     if vals.get('picking_id', False):
    #         pick_obj = self.pool.get('stock.picking')
    #         proc_obj = self.pool.get('procurement.order')
    #         for move in self.browse(cr, uid, ids, context=context):
    #             procurement = False
    #             if vals.get('procurement_id', False):
    #                 procurement = vals['procurement_id']
    #             else:
    #                 procurement = move.procurement_id and \
    #                     move.procurement_id.id or False
    #
    #             if procurement:
    #                 procurement = proc_obj.browse(cr, uid, procurement,
    #                                               context=context)
    #                 if procurement.route_detail_id:
    #                     vls = {
    #                         'route_detail_id':procurement.route_detail_id.id,
    #                         'trans_route_id':procurement.trans_route_id.id
    #                     }
    #                     pick_obj.write(cr, uid, vals['picking_id'], vls,
    #                                    context=context)
    #
    #     # Se evita toda esta parte añadiend el hook de _get_propagated_change_dict
    #     # PAra esto se modificó también el modulo de stock en addons
    #     # Propagar las unidades de venta...
    #     # for move in self.browse(cr, uid, ids, context=context):
    #     #     propagated_changes_dict = {}
    #     #     # propagation of quantity sale change
    #     #     if vals.get('product_uos_qty'):
    #     #         propagated_changes_dict['product_uos_qty'] = \
    #     #             vals['product_uos_qty']
    #     #     if vals.get('product_uos_id'):
    #     #         propagated_changes_dict['product_uos_id'] = \
    #     #             vals['product_uos_id']
    #     #     if not context.get('do_not_propagate', False) and \
    #     #             propagated_changes_dict and move.move_dest_id.id:
    #     #         self.write(cr, uid, [move.move_dest_id.id],
    #     #                    propagated_changes_dict,
    #     #                    context=context)
    #     _logger.debug("CMNT stock.move tiempo total write: %s",
    #                   time.time() - init_t)
    #     return res

    def split(self, cr, uid, move, qty, restrict_lot_id=False,
              restrict_partner_id=False, context=None):
        """
        Cambiar la cantidad de uos al realizar movimientos de Backorder para
        producto con coeff variable
        """
        uos_qty = move.product_uos_qty
        if not move.wait_receipt_qty and move.product_id.is_var_coeff:
            move.write({'product_uom_qty': move.product_uom_qty - qty})
            if move.move_dest_id:
                move.move_dest_id.write({'product_uos_qty': uos_qty })
            return False
        if move.move_dest_id and move.propagate and move.move_dest_id.state \
                not in ('done', 'cancel'):
            self.write(cr, uid, move.move_dest_id.id,
                       {'wait_receipt_qty': move.wait_receipt_qty})

        res = super(stock_move, self).split(cr, uid, move, qty,
                                            restrict_lot_id,
                                            restrict_partner_id,
                                            context=context)
        if move.product_id.is_var_coeff:
            self.write(cr, uid, move.id,
                       {'product_uos_qty': uos_qty - move.wait_receipt_qty})
            split_ids = self.search(cr, uid, [('split_from', '=', move.id)])
            new_uom_split_qty = move.product_id.uos_qty_to_uom_qty(move.wait_receipt_qty, move.product_uos.id)
            self.write(cr, uid, split_ids,
                       {'product_uos_qty': move.wait_receipt_qty,
                        'product_uom_qty': new_uom_split_qty})
        return res

    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type,
                               context=None):
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move,
                                                             partner, inv_type,
                                                             context=context)
        sale_line = move.procurement_id.sale_line_id
        coef = 1
        if inv_type == 'out_invoice' and move.location_id.usage == 'customer':
            coef = -1
        res["uos_id"] = move.product_uom.id
        # if move.product_uos and move.product_uos != move.product_uom and \
        #         move.product_uos_qty:
        if move.product_uos:
            res["second_uom_id"] = move.product_uos.id
            res["quantity_second_uom"] = coef * move.product_uos_qty
        res["quantity"] = coef * move.product_uom_qty
        res['stock_move_id'] = move.id
        if sale_line:
            res["price_unit"] = sale_line.price_unit
        return res

    def action_done(self, cr, uid, ids, context=None):
        """
        Not propagate de date_expected in the move, because of when we complete
        a picking, the move action_done method recalculee it, and is propagated
        to the output picking
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['do_not_propagate'] = True
        res = super(stock_move, self).action_done(cr, uid, ids, context=ctx)
        return res

    @api.one
    def update_receipt_quantity(self, total_operations):
        """
            Updates product_uom_qty and product_uos_qty with operation
            quantities.
            Sets the quantity pending of receipt.
            :param total_operations: dict with total quantity of
                operations in uom and uos
            :returns: None

        """
        same_product_moves = self.picking_id.move_lines.filtered(
            lambda record: record.product_id == self.product_id)
        moves_len = len(same_product_moves)
        total_uos_same_product_moves = sum([x.product_uos_qty for x in
                                            same_product_moves])
        if total_uos_same_product_moves > total_operations['uos']:
            self.wait_receipt_qty = total_uos_same_product_moves - \
                total_operations['uos']
        self.product_uom_qty = total_operations['uom'] / moves_len

        self.product_uos_qty = total_operations['uos'] / moves_len
        if self.move_dest_id:
            self.move_dest_id.product_uom_qty = self.product_uom_qty
            self.move_dest_id.product_uos_qty = self.product_uos_qty

    @api.multi
    def get_backorder_moves(self):
        backorder_moves = self.env['stock.move']
        for move in self:
            if move.wait_receipt_qty and move.product_uos:
                uom_qty = move.product_id.uos_qty_to_uom_qty(
                    move.wait_receipt_qty, move.product_uos.id)
                new_move = move.copy({
                    'product_uom_qty': uom_qty,
                    'product_uos_qty': move.wait_receipt_qty,
                    'wait_receipt_qty': 0,
                    'picking_id': False})
                new_move.purchase_line_id = move.purchase_line_id
                backorder_moves += new_move
        return backorder_moves

    @api.cr_uid_ids_context
    def do_unreserve(self, cr, uid, move_ids, context=None):
        """
        If outgoing picking and all origin pickings are done we put The
        move in confirmed state instead of waiting
        """
        res = super(stock_move, self).do_unreserve(cr, uid, move_ids,
                                                   context=context)
        for move in self.browse(cr, uid, move_ids, context=context):
            if move.picking_id.picking_type_code == 'outgoing' and \
                    move.state == 'waiting':
                change_state = True
                for mv in move.move_orig_ids:
                    if mv.state != 'done':
                        change_state = False
                        break
                if change_state:
                    move.write({'state': 'confirmed'})
        return res

    def _picking_assign(self, cr, uid, move_ids, procurement_group,
                        location_from, location_to, context=None):
        res = super(stock_move, self).\
            _picking_assign(cr, uid, move_ids, procurement_group,
                            location_from, location_to, context=context)
        if move_ids and procurement_group:
            move = self.browse(cr, uid, move_ids[0], context=context)
            if move.picking_id:
                t_group = self.pool.get('procurement.group')
                pg = t_group.browse(cr, uid, procurement_group, context)
                move.picking_id.write({'user_id': pg.user_id.id})
        return res


class stock_inventory(models.Model):

    _inherit = "stock.inventory"

    def _get_available_filters(self, cr, uid, context=None):
        res = super(stock_inventory, self).\
            _get_available_filters(cr, uid, context=context)
        res.append(('category', _('Product Category')))
        return res

    _columns = {
        'category_ids': fields.many2many('product.category',
                                         'product_category_inventory_rel',
                                         'inventory_id', 'categ_id',
                                         string="Categories"),
        'filter': fields.selection(_get_available_filters, 'Selection Filter',
                                   required=True)}

    def _get_inventory_lines(self, cr, uid, inventory, context=None):
        vals = super(stock_inventory, self).\
            _get_inventory_lines(cr, uid, inventory, context=context)
        new_vals = []
        if inventory.category_ids:
            categories = [x.id for x in inventory.category_ids]
            prod_obj = self.pool.get('product.product')
            for pline in vals:
                prod = prod_obj.browse(cr, uid, pline['product_id'],
                                       context=context)
                if prod.categ_id.id in categories:
                    new_vals.append(pline)
        else:
            new_vals = vals

        return new_vals


class stock_picking_wave(models.Model):
    _inherit = "stock.picking.wave"

    _columns = {
        'wave_report_ids': fields.one2many('wave.report', 'wave_id',
                                           'Picking Report'),
        'camera_ids': fields.many2many('stock.location',
                                       'wave_cameras_rel',
                                       'wave_id',
                                       'location_id',
                                       'Cameras picked',
                                       readonly=True),
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                          domain=[('state', '=', 'active')]),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'machine_id': fields.many2one('stock.machine', 'Machine',
                                      readonly=True)}


class stock_quant(models.Model):
    _inherit = 'stock.quant'

    # _columns = {
    #     # Añadir 4 decimales de precissión
    #     'qty': fields.float('Quantity', required=True,
    #                         digits=dp.get_precision
    #                         ('Product Unit of Measure'),
    #                         help="Quantity of products in this quant, in the \
    #                         default unit of measure of the product",
    #                         readonly=True,
    #                         select=True),
    # }

    def apply_removal_strategy(self, cr, uid, location, product, qty, domain,
                               removal_strategy, context=None):
        """
        If not enought qty in the picking location, we search in storage \
        location.
        Then by overwriting action_assign of stock move, we will find the
        reserved quants of storage location.
        If force_quants_location in context wy try to get quants only of
        location
        """
        _logger.debug("CMNT inicio Aplly_removal")
        _logger.debug("CMNT ####################")
        print "removal"
        print location
        print location.usage
        print removal_strategy
        init_t = time.time()
        t_location = self.pool.get('stock.location')
        # When quants already assigned we use the super no midban depot fefo
        already_reserved = False
        for x in domain:
            if x[0] == 'reservation_id' and x[2]:
                already_reserved = True
                removal_strategy = 'fefo'

        #No quiero quants que no pertenezcan a ningún paquete.
        #Buscar esto import
        #import ipdb; ipdb.set_trace()
        #lista de ids donde no se puede buscar producto sin paquete.
        #if location != self.pool.get('stock.warehouse').browse(cr, uid, [1]).wh_output_stock_loc_id
        #domain.append(('package_id', '!=', False))

        if removal_strategy == 'depot_fefo' and not already_reserved and not \
                ('force_quants_location' in context):
            pick_loc_obj = product.picking_location_id
            if location.usage not in ['view', 'internal'] or not pick_loc_obj:
                print "busqueda normal"
                sup = super(stock_quant, self).apply_removal_strategy(
                    cr, uid, location, product, qty, domain, 'fefo',
                    context=context)

                return sup
            #es necesario ordernar antes poqr package id que por
            order = 'removal_date, in_date, package_id, id'
            if not context.get('from_reserve', False):
                # Search quants in picking location
                pick_loc_id = pick_loc_obj.get_general_zone('picking')
                pick_loc = pick_loc_id and \
                    t_location.browse(cr, uid, pick_loc_id) or False
                res = self._quants_get_order(cr, uid, pick_loc, product, qty,
                                             domain, order, context=context)
                check_storage_qty = 0.0
                for record in res:
                    if record[0] is None:
                        check_storage_qty += record[1]
                        res.remove(record)

            storage_id = pick_loc_obj.get_general_zone('storage')
            storage_loc = storage_id and \
                t_location.browse(cr, uid, storage_id) or False

            # Search quants in storage location
            domain = [('reservation_id', '=', False), ('qty', '>', 0)]
            if context.get('from_reserve', False):
                check_storage_qty = qty
                res = []
            if check_storage_qty and storage_loc:
                res += self._quants_get_order(cr, uid, storage_loc, product,
                                              check_storage_qty, domain, order,
                                              context=context)
            #Pending qty?
            check_global_qty = 0.0
            quants_in_res = []

            for record in res:
                if record[0] is None:
                    check_global_qty += record[1]
                    res.remove(record)
                else:
                    quants_in_res.append(record[0].id)
            domain = [('reservation_id', '=', False), ('qty', '>', 0),
                      ('id', 'not in', quants_in_res)]
            if check_global_qty:
                res += self._quants_get_order(cr, uid, location, product,
                                              check_global_qty, domain, order,
                                              context=context)
            _logger.debug("CMNT ####################")
            _logger.debug("CMNT return Aplly_removal %s",time.time() -init_t)

            return res
        elif context.get('force_quants_location', False):
            res = context['force_quants_location']
            if not res:
                raise exceptions.Warning(_('Error!'), _('No quants to force the \
                                                    assignament'))
            return res
        sup = super(stock_quant, self).\
            apply_removal_strategy(cr, uid, location, product, qty, domain,
                                   removal_strategy, context=context)
        print sup
        _logger.debug("CMNT ####################")
        _logger.debug("CMNT return Aplly_removal: %s", time.time() -init_t)

        return sup


class stock_location_rule(models.Model):
    _inherit = "stock.location.route"

    _columns = {
        'cross_dock': fields.boolean('Cross Dock Route',
                                     help="mark to avoid stock virtual"
                                     "conservative warning")}


class stock_production_lot(models.Model):
    _inherit = 'stock.production.lot'
    _columns = {
        'customer_ids': fields.many2many('res.partner', 'customers_lot_rel',
                                         'lot_id', 'partner_id',
                                         'Related customers',
                                         domain=[('customer', '=', True)]),
        'supplier_ids': fields.many2many('res.partner', 'supplier_lot_rel',
                                         'lot_id', 'partner_id',
                                         'Related suppliers',
                                         domain=[('supplier', '=', True)])}


class SrockProductionLot(models.Model):

    _inherit = "stock.production.lot"

    # No pone la traducción ni poniendolo en la vista. Así que en español
    total_lot_qty = fields2.Float('Cantidad total',
                                  compute='_get_lot_qty', readonly=False)

    @api.one
    def _get_lot_qty(self):
        self.total_lot_qty = sum([x.qty for x in self.quant_ids])

###############################################################################
###############################################################################


class stock_config_settings(models.TransientModel):
    _inherit = 'stock.config.settings'

    check_route_zip = fields2.Boolean('Check zips in routes',
                                      help='When adding a customer to a '
                                      'route, imposible to save if customer\
                                       zip is not in route zips')
    check_customer_comercial = fields2.Boolean('Check customer in routes',
                                               help='When adding a customer \
                                               to a route, imposible to save \
                                               if customer is in other route \
                                               of diferent comercial if route \
                                               is not telesale or delivery')
    max_loc_ops = fields2.Integer('Max. location operations',
                                  help='Max. nº of location operations to '
                                  'assign in a location task. If a location '
                                  'has more than this nº of operation the task'
                                  ' wizard will be assign only the max number'
                                  ' this will result in a partial transfer.')
    min_loc_replenish = fields2.Integer('Min locations to replenish',
                                        help='The task wizard will assign the'
                                        ' operations that cover tne indicated'
                                        ' nº of locations to replenish. Maybe'
                                        ' will be transfer several replenish'
                                        ' pickings')
    mandatory_camera = fields2.Boolean('Mandarory camera',
                                       help='If checked when you ask for a \
                                       reposition or ubication task you must \
                                       set the camera or cameras to get \
                                       operations')
    check_sale_order = fields2.Boolean('Check route in sale order',
                                       help='If checked, when you try confirm \
                                       a sale order you will not be able to do\
                                       it if there is no a delivery route \
                                       detail scheduled for the customer')
    pick_by_volume = fields2.Boolean('Picking task by volume',
                                     help='If checked when we get a picking\
        task, from all moves of a kind of product we only put in the task \
        moves until reach the max volume. If max volume is reached it will be\
        ignored all product moves and continues with other product moves\
        If not checked all moves of a route and a concret date will be\
        considered in a unique task without limit.')
    print_report = fields2.Boolean('Print report task when get a task',
                                   help='If checked, when you get a \
        reposition or picking task the report will be printed')
    max_per_filled = fields2.Float('Max. Percentage Filled',
                                   help='In percentage if zero not counted,\
                                   It is a limit that \
                                   considers an ubicartion as filled when \
                                   it reaches the specific percentatage.')

    @api.multi
    def get_default_check_route_zip(self, fields):
        domain = [('key', '=', 'check.route.zip')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = True if param_obj.value == 'True' else False
        return {'check_route_zip': value}

    @api.multi
    def set_default_check_route_zip(self):
        domain = [('key', '=', 'check.route.zip')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = 'True' if self.check_route_zip else 'False'

    @api.multi
    def get_default_customer_comercial(self, fields):
        domain = [('key', '=', 'check.customer.comercial')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = True if param_obj.value == 'True' else False
        return {'check_customer_comercial': value}

    @api.multi
    def set_default_customer_comercial(self):
        domain = [('key', '=', 'check.customer.comercial')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = 'True' if self.check_customer_comercial else 'False'

    @api.multi
    def get_default_max_loc_ops(self, fields):
        domain = [('key', '=', 'max.loc.ops')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = int(param_obj.value)
        return {'max_loc_ops': value}

    @api.multi
    def set_max_loc_ops(self):
        domain = [('key', '=', 'max.loc.ops')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = str(self.max_loc_ops)

    @api.multi
    def get_default_min_loc_replenish(self, fields):
        domain = [('key', '=', 'min.loc.replenish')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = int(param_obj.value)
        return {'min_loc_replenish': value}

    @api.multi
    def set_min_loc_replenish(self):
        domain = [('key', '=', 'min.loc.replenish')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = str(self.min_loc_replenish)

    @api.multi
    def get_default_mandatory_camera(self, fields):
        domain = [('key', '=', 'mandatory.camera')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = True if param_obj.value == 'True' else False
        return {'mandatory_camera': value}

    @api.multi
    def set_default_mandatory_camera(self):
        domain = [('key', '=', 'mandatory.camera')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = 'True' if self.mandatory_camera else 'False'

    @api.multi
    def get_default_check_sale_order(self, fields):
        domain = [('key', '=', 'check.sale.order')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = True if param_obj.value == 'True' else False
        return {'check_sale_order': value}

    @api.multi
    def set_default_check_sale_order(self):
        domain = [('key', '=', 'check.sale.order')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = 'True' if self.check_sale_order else 'False'

    @api.multi
    def get_default_pick_by_volume(self, fields):
        domain = [('key', '=', 'pick.by.volume')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = True if param_obj.value == 'True' else False
        return {'pick_by_volume': value}

    @api.multi
    def set_default_pick_by_volume(self):
        domain = [('key', '=', 'pick.by.volume')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = 'True' if self.pick_by_volume else 'False'

    @api.multi
    def get_default_print_report(self, fields):
        domain = [('key', '=', 'print.report')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = True if param_obj.value == 'True' else False
        return {'print_report': value}

    @api.multi
    def set_print_report(self):
        domain = [('key', '=', 'print.report')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = 'True' if self.print_report else 'False'

    @api.multi
    def get_default_max_per_filled(self, fields):
        domain = [('key', '=', 'max.per.filled')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = float(param_obj.value)
        return {'max_per_filled': value}

    @api.multi
    def set_max_per_filled(self):
        domain = [('key', '=', 'max.per.filled')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = str(self.max_per_filled)
