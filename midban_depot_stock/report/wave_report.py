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


class sale_report(osv.osv):
    _name = "wave.report"
    _description = "Group picks of waves"
    _auto = False
    _rec_name = 'product_id'
    _order = 'sequence'

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
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            item_res = []
            # import ipdb; ipdb.set_trace()
            for pick in item.wave_id.picking_ids:
                for op in pick.pack_operation_ids:
                    if op.location_id == item.location_id:
                        if op.package_id:
                            if op.package_id.id == item.pack_id.id:
                                item_res.append(op.id)
                        else:
                            if op.product_id == item.product_id and \
                                    op.lot_id == item.lot_id:
                                item_res.append(op.id)
            res[item.id] = list(set(item_res))
        return res

    def _set_operation_ids(self, cr, uid, ids, field_name, values, args,
                           context=None):
        if values:
            pack_op_obj = self.pool['stock.pack.operation']

            for value in values:
                vals_action, vals_id, vals = value

                if vals_action == 0:
                    # raise exceptions.Warning(_("It is not possible
                    # create new"
                    #                           " records in this field"))
                    pack_op_obj.create(cr, uid, vals)
                elif vals_action == 1:
                    vals['changed'] = True
                    pack_op_obj.write(cr, uid, [vals_id], vals)
                elif vals_action == 2:
                    pack_op_obj.unlink(cr, uid, [vals_id])

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
        'sequence': fields.integer('Sequence', readonly=True),
        'wave_id': fields.many2one('stock.picking.wave', 'Wave',
                                   readonly=True),
        'camera_id': fields.function(_get_camera_from_loc, type='many2one',
                                     relation='stock.location',
                                     string='Camera', readonly=True),
        'operation_ids': fields.function(_get_operation_ids, type="one2many",
                                         string="Operations",
                                         relation="stock.pack.operation",
                                         fnct_inv=_set_operation_ids),
        'uom_id': fields.related('product_id', 'uom_id', type='many2one',
                                 relation='product.uom', string='Stock unit',
                                 readonly=True),
        'uos_qty': fields.float('UoS quantity', readonly=True),
        'uos_id': fields.many2one('product.uom', 'Secondary unit',
                                  readonly=True),
        'customer_id': fields.many2one('res.partner', 'Customer',
                                      readonly=True),
        'pack_id': fields.many2one('stock.quant.package', 'Pack',
                                      readonly=True)
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
          SUM(SQ.uos_qty)         AS uos_qty,
          SQ.uos_id          AS uos_id,
          SQ.customer_id       AS customer_id,
          SQ.pack_id      as pack_id"""

    def _subquery_grouped_op(self):
        return """SELECT Min(operation.id) AS id,
                  quant.product_id  AS product_id,
                  quant.lot_id      AS lot_id,
                  operation.location_id,
                  SUM(operation.uos_qty) AS uos_qty,
                  operation.uos_id AS uos_id,
                  SUM(quant.qty)    AS product_qty,
                  wave.id           AS wave_id,
                  location.sequence AS sequence,
                  quant.package_id as pack_id,
                  0 as customer_id

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
           WHERE  (operation.product_id IS NULL AND
            product_template.is_var_coeff = false) or (operation.product_id IS
            NULL AND product_template.is_var_coeff is null)
           GROUP  BY quant.product_id,
                     quant.lot_id,
                     operation.location_id,
                     operation.uos_id,
                     wave.id,
                     customer_id,
                     pack_id,
                     sequence
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
                  operation.package_id as pack_id,
                  0 as customer_id

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
           WHERE  (operation.product_id IS NOT NULL AND
           product_template.is_var_coeff = false) or (operation.product_id
           IS NOT NULL AND product_template.is_var_coeff is null)
           GROUP  BY operation.product_id,
                     operation.lot_id,
                     operation.location_id,
                     operation.uos_id,
                     wave.id,
                     pack_id,
                     customer_id,
                     sequence"""

    def _subquery_no_grouped_op(self):
        return """SELECT Min(operation.id) AS id,
                  quant.product_id  AS product_id,
                  quant.lot_id      AS lot_id,
                  operation.location_id,
                  SUM(operation.uos_qty) AS uos_qty,
                  operation.uos_id AS uos_id,
                  SUM(quant.qty)    AS product_qty,
                  wave.id           AS wave_id,
                  location.SEQUENCE AS SEQUENCE,
                  picking.partner_id as customer_id,
                  quant.package_id as pack_id

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
           WHERE  operation.product_id IS NULL
           AND product_template.is_var_coeff = true
           GROUP  BY quant.product_id,
                     quant.lot_id,
                     operation.location_id,
                     operation.uos_id,
                     wave.id,
                     pack_id,
                     customer_id,
                     sequence
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
                  picking.partner_id as customer_id,
                  operation.package_id as pack_id
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
           WHERE  operation.product_id IS NOT NULL
           AND product_template.is_var_coeff = true
           GROUP  BY operation.product_id,
                     operation.lot_id,
                     operation.location_id,
                     operation.uos_id,
                     wave.id,
                     pack_id,
                     customer_id,
                     sequence"""

    def _group_by(self):
        return """SQ.product_id,
             SQ.lot_id,
             SQ.location_id,
             SQ.wave_id,
             SQ.sequence,
             SQ.uos_id,
             SQ.pack_id,
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
