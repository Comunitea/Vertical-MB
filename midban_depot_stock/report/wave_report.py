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

from openerp import tools
from openerp.osv import fields, osv
from openerp import models, api
import time
import logging
_logger = logging.getLogger(__name__)
from openerp.exceptions import except_orm
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare


class wave_report(osv.osv):
    _name = "wave.report"
    _description = "Group picks of waves"
    _auto = False
    _rec_name = 'product_id'
    _order = 'order_seq, pack_id'

    def _get_camera_from_loc(self, cr, uid, ids, field_names, args,
                             context=None):
        if context is None:
            context = {}
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = False
            if item.location_id:
                res[item.id] = item.location_id.get_camera()
        return res

    def _get_operation_ids(self, cr, uid, ids, field_names, args,
                           context=None):
        _logger.debug("CMNT _get_operation_ids")
        init_t = time.time()
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            process = True
            visited = True
            item_res = []
            for pick in item.wave_id.picking_ids:
                for op in pick.pack_operation_ids:
                    # Para revisar por OMAR
                    if op.location_id == item.location_id and \
                            (not item.customer_id or  item.customer_id.id == op.picking_id.partner_id.id):
                        if op.package_id:
                            if op.package_id.id == item.pack_id.id and\
                                    (not item.uos_id or op.uos_id == item.uos_id) and\
                                    op.op_package_id == item.op_package_id:
                                item_res.append(op.id)
                                if not op.to_process:
                                    process = False
                                if not op.visited:
                                    visited = False
                        else:
                            if op.product_id == item.product_id and \
                                    op.lot_id == item.lot_id and\
                                    (not item.uos_id or op.uos_id == item.uos_id) and\
                                    op.op_package_id == item.op_package_id:
                                item_res.append(op.id)
                                if not op.to_process:
                                    process = False
                                if not op.visited:
                                    visited = False
            res[item.id]= {}
            res[item.id]['operation_ids'] = list(set(item_res))
            res[item.id]['to_process'] = process
            res[item.id]['visited'] = visited
        _logger.debug("CMNT time _get_operation_ids %s", time.time() - init_t)
        return res

    def _set_operation_ids(self, cr, uid, ids, field_name, values, args,
                           context=None):
        _logger.debug("CMNT _set_operation_ids")
        init_t = time.time()
        ctx = context.copy()
        ctx['no_recompute'] = True
        if values:
            pack_op_obj = self.pool['stock.pack.operation']

            for value in values:
                vals_action, vals_id, vals = value

                if vals_action == 0:
                    # raise exceptions.Warning(_("It is not possible
                    # create new"
                    #                           " records in this field"))
                    pack_op_obj.create(cr, uid, vals, ctx)
                elif vals_action == 1:
                    vals['changed'] = True
                    pack_op_obj.write(cr, uid, [vals_id], vals, ctx)
                elif vals_action == 2:
                    pack_op_obj.unlink(cr, uid, [vals_id])
        _logger.debug("CMNT time _set_operation_ids %s", time.time() - init_t)
        return True

    _columns = {
        'product_id': fields.many2one('product.product', 'Product',
                                      readonly=True),
        'reference': fields.related('product_id', 'default_code', type='char',
                                    string='Reference', size=128,
                                    readonly=True),
        'ean13': fields.related('product_id', 'ean13', type='char',
                                string='EAN 13', size=128, readonly=True),
        'location_id': fields.many2one('stock.location', 'Location',
                                       readonly=True),
        'product_qty': fields.float('Quantity', readonly=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot',
                                  readonly=True),
        'order_seq': fields.char('Sequence'),
        'sequence': fields.integer('Sequence', readonly=True),
        'wave_id': fields.many2one('stock.picking.wave', 'Wave',
                                   readonly=True),
        'camera_id': fields.function(_get_camera_from_loc, type='many2one',
                                     relation='stock.location',
                                     string='Camera', readonly=True),
        'operation_ids': fields.function(_get_operation_ids, type="one2many",
                                         string="Operations",
                                         relation="stock.pack.operation",
                                         fnct_inv=_set_operation_ids, multi='multi_'),
        'uom_id': fields.related('product_id', 'uom_id', type='many2one',
                                 relation='product.uom', string='Stock unit',
                                 readonly=True),
        'uos_qty': fields.float('UoS quantity', readonly=True,
                                digits_compute=
                                dp.get_precision('Product Unit of Measure')),
        'uos_id': fields.many2one('product.uom', 'Secondary unit',
                                  readonly=True),
        'customer_id': fields.many2one('res.partner', 'Customer',
                                       readonly=True),
        'pack_id': fields.many2one('stock.quant.package', 'Pack',
                                   readonly=True),
        'op_package_id': fields.many2one('stock.quant.package', 'OP Package',
                                   readonly=True),
        'to_process': fields.function(_get_operation_ids, type="boolean",
                                         string="Processed (All Ops)",
                                         relation="stock.pack.operation",
                                         multi='multi_'),
        'visited': fields.function(_get_operation_ids, type="boolean",
                                         string="Visited (All Ops)",
                                         relation="stock.pack.operation",
                                         multi='multi_'),
        'is_package': fields.boolean('Is Package'),

    }

    def _select(self):
        return """
          Min(SQ.id)          AS id,
          SQ.product_id       AS product_id,
          SQ.lot_id           AS lot_id,
          SQ.location_id      AS location_id,
          SUM(SQ.product_qty) AS product_qty,
          SQ.wave_id          AS wave_id,
          SQ.sequence         AS sequence,
          SQ.order_seq         AS order_seq,
          SUM(SQ.uos_qty)         AS uos_qty,
          SQ.uos_id          AS uos_id,
          SQ.customer_id       AS customer_id,
          SQ.is_package         as is_package,
          SQ.op_package_id as op_package_id,
          SQ.to_process as to_process,
          SQ.pack_id      as pack_id"""

    def _subquery_grouped_op(self):
        # 1º Paquete completo, peso fijo.
        # 2º Cantidad de producto, peso fijo.
        return """SELECT Min(operation.id) AS id,
                  quant.product_id  AS product_id,
                  quant.lot_id      AS lot_id,
                  operation.location_id,
                  0 AS uos_qty,
                  0 AS uos_id,
                  SUM(quant.qty)    AS product_qty,
                  wave.id           AS wave_id,
                  location.sequence AS sequence,
                  location.order_seq AS order_seq,
                  quant.package_id as pack_id,
                  0 as customer_id,
                  true as is_package,
                  op_package_id as op_package_id,
                  operation.to_process as to_process


           FROM   stock_quant quant
                  inner join stock_quant_package PACKAGE
                          ON PACKAGE.id = quant.package_id
                  inner join stock_pack_operation operation
                          ON operation.package_id = PACKAGE.id
                  inner join stock_picking picking
                          ON picking.id = operation.picking_id
                  inner join stock_picking_wave wave
                          ON wave.id = picking.wave_id
                  inner join stock_location location
                          ON location.id = operation.location_id
                  inner join product_product product
                          ON product.id = quant.product_id
                  inner join product_template product_template
                          ON product_template.id = product.product_tmpl_id
           WHERE  ((operation.product_id IS NULL AND
            product_template.is_var_coeff = false) or (operation.product_id IS
            NULL AND product_template.is_var_coeff is null))  and
           (picking.state in ('assigned', 'partially_available', 'done'))
           GROUP  BY quant.product_id,
                     quant.lot_id,
                     operation.location_id,
                     wave.id,
                     customer_id,
                     pack_id,
                     sequence,
                     order_seq,
                     is_package,
                     op_package_id,
                     operation.to_process
           UNION
           SELECT Min(operation.id)          AS id,
                  operation.product_id       AS product_id,
                  operation.lot_id           AS lot_id,
                  operation.location_id,
                  0 AS uos_qty,
                  0 AS uos_id,
                  SUM(operation.product_qty) AS product_qty,
                  wave.id                       AS wave_id,
                  location.sequence AS sequence,
                  location.order_seq AS order_seq,
                  operation.package_id as pack_id,
                  0 as customer_id,
                  false as is_package,
                  op_package_id as op_package_id,
                  operation.to_process as to_process

           FROM   stock_pack_operation operation
                  inner join stock_picking picking
                          ON picking.id = operation.picking_id
                  inner join stock_picking_wave wave
                          ON wave.id = picking.wave_id
                  inner join stock_location location
                          ON location.id = operation.location_id
                  inner join product_product product
                          ON product.id = operation.product_id
                  inner join product_template product_template
                          ON product_template.id = product.product_tmpl_id
           WHERE  ((operation.product_id IS NOT NULL AND
           product_template.is_var_coeff = false) or (operation.product_id
           IS NOT NULL AND product_template.is_var_coeff is null))  and
           (picking.state in ('assigned', 'partially_available', 'done'))
           GROUP  BY operation.product_id,
                     operation.lot_id,
                     operation.location_id,
                     wave.id,
                     customer_id,
                     pack_id,
                     sequence,
                     is_package,
                     op_package_id,
                     operation.to_process,
                     order_seq"""

    def _subquery_no_grouped_op(self):
        #1º Paquete Completo, producto variable
        #2º Cantidad de producto, producto variable
        return """SELECT Min(operation.id) AS id,
                  quant.product_id  AS product_id,
                  quant.lot_id      AS lot_id,
                  operation.location_id,
                  MIN(operation.uos_qty) AS uos_qty,
                  operation.uos_id AS uos_id,
                  SUM(quant.qty)    AS product_qty,
                  wave.id           AS wave_id,
                  location.SEQUENCE AS SEQUENCE,
                  location.order_seq AS order_seq,
                  quant.package_id as pack_id,
                  picking.partner_id as customer_id,
                  true as is_package,
                  op_package_id as op_package_id,
                  operation.to_process as to_process

           FROM   stock_quant quant
                  inner join stock_quant_package PACKAGE
                          ON PACKAGE.id = quant.package_id
                  inner join stock_pack_operation operation
                          ON operation.package_id = PACKAGE.id
                  inner join stock_picking picking
                          ON picking.id = operation.picking_id
                  inner join stock_picking_wave wave
                          ON wave.id = picking.wave_id
                  inner join stock_location location
                          ON location.id = operation.location_id
                  inner join product_product product
                          ON product.id = quant.product_id
                  inner join product_template product_template
                          ON product_template.id = product.product_tmpl_id
           WHERE  (operation.product_id IS NULL
           AND product_template.is_var_coeff = true)  and
           (picking.state in ('assigned', 'partially_available', 'done'))
           GROUP  BY quant.product_id,
                     quant.lot_id,
                     operation.location_id,
                     operation.uos_id,
                     wave.id,
                     customer_id,
                     pack_id,
                     sequence,
                     order_seq,
                     is_package,
                     op_package_id,
                     operation.to_process
           UNION
           SELECT Min(operation.id)          AS id,
                  operation.product_id       AS product_id,
                  operation.lot_id           AS lot_id,
                  operation.location_id,
                  SUM(operation.uos_qty) AS uos_qty,
                  operation.uos_id AS uos_id,
                  SUM(operation.product_qty) AS product_qty,
                  wave.id                       AS wave_id,
                  location.sequence                 AS sequence,
                  location.order_seq AS order_seq,
                  operation.package_id as pack_id,
                  picking.partner_id as customer_id,
                  false as is_package,
                  op_package_id as op_package_id,
                  operation.to_process as to_process

           FROM   stock_pack_operation operation
                  inner join stock_picking picking
                          ON picking.id = operation.picking_id
                  inner join stock_picking_wave wave
                          ON wave.id = picking.wave_id
                  inner join stock_location location
                          ON location.id = operation.location_id
                  inner join product_product product
                          ON product.id = operation.product_id
                  inner join product_template product_template
                          ON product_template.id = product.product_tmpl_id
           WHERE  (operation.product_id IS NOT NULL
           AND product_template.is_var_coeff = true) and
           (picking.state in ('assigned', 'partially_available', 'done'))
           GROUP  BY operation.product_id,
                     operation.lot_id,
                     operation.location_id,
                     operation.uos_id,
                     wave.id,
                     customer_id,
                     pack_id,
                     sequence,
                     is_package,
                     op_package_id,
                     order_seq,
                     operation.to_process"""

    def _group_by(self):
        return """SQ.product_id,
             SQ.lot_id,
             SQ.location_id,
             SQ.wave_id,
             SQ.sequence,
             SQ.order_seq,
             SQ.uos_id,
             SQ.pack_id,
             SQ.is_package,
             SQ.op_package_id,
             SQ.to_process,
             SQ.customer_id"""

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT %s
               FROM   ((%s)
                        UNION

                        (%s)

                                 )SQ
               GROUP  BY %s
                        )""" % (self._table, self._select(), self._subquery_grouped_op(),
                                self._subquery_no_grouped_op(), self._group_by()))

    def _change_original_op_vals(self, op, op_qty, qty_to_create):
        vals = {}
        prod = op.operation_product_id
        new_qty = op_qty - qty_to_create
        new_uos_qty = prod.uom_qty_to_uos_qty(new_qty, op.uos_id.id)
        vals = {
            'product_id': prod.id,
            'product_qty': new_qty,
            'uos_qty': new_uos_qty,
            'lot_id': op.package_id.packed_lot_id.id
        }
        return vals

    def _get_new_op_vals(self, op, op_qty, pack, qty_to_create, needed_qty, task_id):
        vals = {}
        prod = pack.product_id
        move_pack = False
        if pack.packed_qty == needed_qty:
            move_pack = True
        new_qty = 1 if move_pack else qty_to_create
        new_uos_qty = prod.uom_qty_to_uos_qty(new_qty, pack.uos_id.id)
        vals = {
            'product_id': False if move_pack else prod.id,
            'product_qty': 1 if move_pack else new_qty,
            'product_uom_id': False if move_pack else prod.uom_id.id,
            'lot_id': False if move_pack else pack.packed_lot_id.id,
            'package_id': pack.id,
            'uos_qty': new_uos_qty,
            'uos_id': op.uos_id.id,
            'location_id': pack.location_id.id,
            'location_dest_id': op.location_dest_id.id,
            'picking_id': op.picking_id.id,
            'task_id': task_id

        }
        return vals

    def _sust_original_op_vals(self, op, op_qty, pack, qty_to_create,
                               needed_qty):
        vals = {}
        prod = pack.product_id
        move_pack = False
        if pack.packed_qty == needed_qty:
            move_pack = True
        new_qty = 1 if move_pack else op_qty
        new_uos_qty = prod.uom_qty_to_uos_qty(op.product_qty, pack.uos_id.id)
        vals = {
            'product_id': prod.id,
            'product_qty': new_qty,
            'product_uom_id': prod.uom_id.id,
            'lot_id': pack.packed_lot_id.id,
            'package_id': pack.id,
            'uos_qty': new_uos_qty,
            'uos_id': pack.uos_id.id,
            'location_id': pack.location_id.id,
        }
        return vals

    @api.multi
    def create_operations_on_the_fly_from_gun(self, my_args):
        wave_report_id = my_args.get('wave_report_id', False)
        needed_qty= my_args.get('needed_qty', 0)
        pack_id= my_args.get('pack_id', False)
        user_id = my_args.get('user_id', False)
        return self.create_operations_on_the_fly(wave_report_id, needed_qty, pack_id)

    def create_operations_on_the_fly(self, wave_report_id, needed_qty, pack_id):
        created_qty = 0.0
        t_op = self.env['stock.pack.operation']
        t_pa = self.env['stock.quant.package']
        wave_report = self.browse(wave_report_id)
        if wave_report.wave_id.state in ['done', 'cancel']:
            raise except_orm(_('Error'), _('You can not change operations in \
                                            a done or cancelled wave'))
        op_objs = wave_report.operation_ids
        op_objs = sorted(op_objs, key=lambda op: op.product_qty)
        qty_to_create = needed_qty
        pack = t_pa.browse(pack_id)
        if not pack:
            raise except_orm(_('Error'),
                             _('You must select a pack to add operations'))
        for op in op_objs:
            if op.picking_id.state not in ['assigned']:
                err = _("You can not change operations in picking %s because \
                         it isn't in ready to transfer \
                         state" % op.picking_id.name)
                raise except_orm(_('Error'), err)
            op_qty = op.product_qty if op.product_id else \
                op.package_id.packed_qty
            if op_qty > qty_to_create:
                task_id = op.task_id.id
                change_vals = self._change_original_op_vals(op, op_qty,
                                                            qty_to_create)
                op.write(change_vals)
                new_vals = self._get_new_op_vals(op, op_qty, pack,
                                                 qty_to_create, needed_qty, task_id)
                t_op = t_op.create(new_vals)
                created_qty += new_vals.get('product_qty', 0.0)
                break
            else:
                sust_vals = self._sust_original_op_vals(op, op_qty, pack,
                                                        qty_to_create,
                                                        needed_qty)
                op.write(sust_vals)
                created_qty += sust_vals.get('product_qty', 0.0)
                qty_to_create -= created_qty
                if not qty_to_create:
                    break
        return created_qty


class wave_report_parser(models.AbstractModel):
    """ Parser to group products in camaras"""

    _name = 'report.midban_depot_stock.report_picking_list'

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report_name = 'midban_depot_stock.report_picking_list'
        report = report_obj._get_report_from_name(report_name)
        docs = []
        products = {}
        for wave in self.env[report.model].browse(self._ids):
            docs.append(wave)
            for line in wave.wave_report_ids:
                if line.camera_id not in products:
                    products[line.camera_id] = [line]
                else:
                    products[line.camera_id].append(line)
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': docs,
            'products': products,
        }
        return report_obj.render(report_name, docargs)
