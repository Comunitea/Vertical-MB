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
from openerp.osv import osv, fields
from openerp import api, models
from openerp import fields as fields2
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import math


class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _order = "name desc"
    _columns = {
        'operator_id': fields.many2one('res.users', 'Operator',
                                       readonly=True,
                                       domain=[('operator', '=', 'True')]),
        'machine_id': fields.many2one('stock.machine', 'Machine',
                                      readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse',
                                        'Moves warehouse', readonly=True),
        'task_type': fields.selection([('ubication', 'Ubication',),
                                       ('reposition', 'Reposition'),
                                       ('picking', 'Picking')],
                                      'Task Type', readonly=True),
        # 'trans_route_id': fields.many2one('route', 'Transport Route',
        #                                   readonly=True),
        'route_detail_id': fields.many2one('route.detail', 'Detail Route',
                                           domain=[('state', '=', 'active')]),
        'trans_route_id': fields.related('route_detail_id', 'route_id',
                                         string='Transport Route',
                                         type="many2one",
                                         relation="route",
                                         store=True,
                                         readonly=True),
        'detail_date': fields.related('route_detail_id', 'date',
                                      string='Route Date',
                                      type="date",
                                      relation="route.detail",
                                      store=True,
                                      readonly=True),
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
                                     type="char", string="Order Note"),
    }

    def _change_operation_dest_loc(self, cr, uid, ids, context=None):
        """
        If picking is inncoming. for each operation in the pickings,
        get the location from the package
        """
        # t_operation = self.pool.get('stock.pack.operation')
        if context is None:
            context = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.picking_type_code == 'incoming' and \
                    pick.move_lines and pick.move_lines[0].move_dest_id:
                related_pick_id = pick.move_lines[0].move_dest_id.picking_id.id
                related_pick = pick.move_lines[0].move_dest_id.picking_id
                related_pick.do_prepare_partial()
                for op in related_pick.pack_operation_ids:
                    pack_id = op.package_id.id
                    for op2 in pick.pack_operation_ids:
                        if op2.result_package_id.id == pack_id:
                            op.write({'location_dest_id':
                                      op2.chained_loc_id.id})
                            break
                self.write(cr, uid, [related_pick_id],
                           {'midban_operations': True}, context=context)
        return True

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
                    'processed': 'true'
                })
        self.do_transfer(cr, uid, ids, context=context)
        # Prepare operations for the next chained picking if it exist
        self._change_operation_dest_loc(cr, uid, ids, context=context)
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
        t_transfer = self.env['stock.transfer_details']
        t_item = self.env['stock.transfer_details_items']
        transfer_obj = t_transfer.create({'picking_id': self.id})
        pending_ops_vals = []
        something_done = False
        for op in self.pack_operation_ids:
            if op.to_process and op.task_id and op.task_id.id == task_id:
                item = {
                    'packop_id': op.id,
                    'product_id': op.product_id.id,
                    'product_uom_id': op.product_uom_id.id,
                    'quantity': op.product_qty,
                    'package_id': op.package_id.id,
                    'lot_id': op.lot_id.id,
                    'sourceloc_id': op.location_id.id,
                    'destinationloc_id': op.location_dest_id.id,
                    'result_package_id': op.result_package_id.id,
                    'date': op.date,
                    'owner_id': op.owner_id.id,
                    'transfer_id': transfer_obj.id,
                }
                t_item.create(item)
                something_done = True
            else:
                assigned_task_id = False  # If marked to not do deassign it
                if op.to_process and op.task_id:  # Conservate the task
                    assigned_task_id = op.task_id.id

                new_ops_vals = {
                    'product_id': op.product_id.id,
                    'product_uom_id': op.product_uom_id.id,
                    'product_qty': op.product_qty,
                    'package_id': op.package_id.id,
                    'lot_id': op.lot_id.id,
                    'location_id': op.location_id.id,
                    'location_dest_id': op.location_dest_id.id,
                    'result_package_id': op.result_package_id.id,
                    'owner_id': op.owner_id.id,
                    'task_id': assigned_task_id,
                    'to_process': True,
                    'old_id': op.id,
                    # To remember the original operation when we scan a barcode
                    # in warehouse_scan_gun_module, because maybe the assigned
                    # operation were deleted by doinf a partial picking.
                }
                pending_ops_vals.append(new_ops_vals)

        if something_done:
            transfer_obj.do_detailed_transfer()
            new_pick_obj = self.search([('backorder_id', '=', self.id)])
            if new_pick_obj and pending_ops_vals:
                for vals in pending_ops_vals:
                    vals['picking_id'] = new_pick_obj.id
                    new_pick_obj.write({'pack_operation_ids': [(0, 0, vals)]})
        else:
            for op in self.pack_operation_ids:
                op.task_id = False  # Write to be able to assign later
                op.to_process = True  # Write to be to process by default
        return


class stock_package(osv.osv):
    _inherit = "stock.quant.package"

    def _get_package_lot_id(self, cr, uid, ids, name, args, context=None):
        """
        Returns lot of products inside the QUANTS of the pack.
        We not check childrens packages. # TODO??
        We assume no exist pack of diferents lots, in that case return False.
        """
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            lot_id = False
            for quant in pack.quant_ids:
                lot_id = quant.lot_id and quant.lot_id.id or False
                if lot_id != quant.lot_id.id:  # Founded diferents lots in pack
                    lot_id = False
            res[pack.id] = lot_id
        return res

    def _get_packed_qty(self, cr, uid, ids, name, args, context=None):
        """
        Returns units qty inside the QUANTS of the pack.
        We not check childrens packages. # TODO??
        We assume no exist pack of diferents lots, in that case return False.
        """
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            qty = 0.0
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
            if pack.pack_type:
                if pack.pack_type == 'palet' and pack.product_id:
                    units_in_mantle = pack.product_id.un_ca * \
                        pack.product_id.ca_ma
                    if units_in_mantle:
                        mantles = math.ceil(pack.packed_qty / units_in_mantle)
                        mantles = int(mantles)
            res[pack.id] = mantles
        return res

    def _get_pack_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        no_wood = context.get('no_wood', False)
        res = {}
        t_loc = self.pool.get('stock.location')
        for pack in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            loc_dest_obj = t_loc.browse(cr, uid, pack.location_id.id,
                                        context=context)
            if pack.pack_type == 'box':  # No multiproduct
                prod = pack.product_id
                volume = prod.ca_width * prod.ca_height * prod.ca_length
            elif pack.pack_type == 'palet':  # Maybe multiproduct
                quants_by_prod = {}
                # Group quants inside the package by product
                quants_by_prod = pack.get_products_quants()
                width_wood = 0
                length_wood = 0
                sum_heights = 0
                wood_height = 0
                for product in quants_by_prod:
                    # Get product with maximun base by the width
                    if product.pa_width > width_wood:
                        width_wood = product.pa_width
                        length_wood = product.pa_length
                        wood_height = product.palet_wood_height
                    quant_lst = quants_by_prod[product]
                    qty = 0
                    for quant in quant_lst:
                        qty += quant.qty

                    mantle_units = product.un_ca * product.ca_ma
                    num_mantles = int(math.ceil(qty / mantle_units))
                    mantle_height = product.ma_height
                    sum_heights += num_mantles * mantle_height

                # No wood in picking location, it will be added later
                if loc_dest_obj.zone == 'picking' or no_wood:
                    wood_height = 0
                sum_heights += wood_height  # Add wood height
                volume = width_wood * length_wood * sum_heights
            res[pack.id] = volume
        return res

    def _is_multiproduct_pack(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            product_id = False
            is_multiproduct = False
            for quant in pack.quant_ids:
                product_id = quant.product_id.id
                if product_id != quant.lot_id.id:  # Founded diferents products
                    is_multiproduct = True
                    break
            res[pack.id] = is_multiproduct
        return res

    _columns = {
        'pack_type': fields.selection([('box', 'Box'),
                                       ('palet', 'Palet')],
                                      # ('var_palet', 'Var Palet')],
                                      'Pack Type'),
        'product_id': fields.related('quant_ids', 'product_id', readonly=True,
                                     type="many2one", string="Product",
                                     relation="product.product"),
        'packed_lot_id': fields.function(_get_package_lot_id,
                                         string="Packed Lot",
                                         readonly=True,
                                         type="many2one",
                                         relation="stock.production.lot"),

        'packed_qty': fields.function(_get_packed_qty, type="float",
                                      string="Packed qty",
                                      readonly=True,
                                      digits_compute=dp.get_precision
                                      ('Product Price'),),
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
                                           string="Is multiproduct")
    }

    def get_products_quants(self, cr, uid, ids, context=None):
        """
        Returns a dictionary containing the quants for each product
        """
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


class stock_pack_operation(osv.osv):
    _inherit = "stock.pack.operation"

    def _get_pack_type(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for ops in self.browse(cr, uid, ids, context=context):
            res[ops.id] = False
            pack_type = False
            if ops.package_id:
                pack_type = ops.package_id.pack_type
            elif ops.result_package_id:
                pack_type = ops.result_package_id.pack_type
            if pack_type:
                res[ops.id] = pack_type
        return res

    def _get_real_product(self, cr, uid, ids, name, args, context=None):
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
        if context is None:
            context = {}
        res = {}
        for ope in self.browse(cr, uid, ids, context=context):
            res[ope.id] = 0
            if ope.package_id:
                if ope.package_id.pack_type == 'palet':
                    res[ope.id] = ope.package_id.num_mantles
                # If quit from a pack and put in other pack return the
                # operation num_mantles instead of the volume
                if ope.result_package_id and ope.product_qty:
                    units_in_mantle = ope.product_id.un_ca * \
                        ope.product_id.ca_ma
                    if units_in_mantle:
                        mantles = math.ceil(ope.product_qty / units_in_mantle)
                        mantles = int(mantles)
                        res[ope.id] = mantles
            elif ope.product_id and ope.product_qty \
                    and ope.result_package_id \
                    and ope.result_package_id.pack_type == 'palet':
                un_ca = ope.product_id.un_ca
                ca_ma = ope.product_id.ca_ma
                mant_units = un_ca * ca_ma
                if mant_units:
                    res[ope.id] = int(math.ceil(ope.product_qty / mant_units))
        return res

    def _get_qty_package(self, cr, uid, ids, name, args, context=None):
        """
        Get the qty inside the package or the qty going to a new package
        """
        if context is None:
            context = {}
        res = {}
        for ope in self.browse(cr, uid, ids, context=context):
            res[ope.id] = 0
            if ope.package_id:
                res[ope.id] = ope.package_id.packed_qty
            elif ope.result_package_id and ope.product_qty:
                res[ope.id] = ope.product_qty
        return res

    _columns = {
        'pack_type': fields.function(_get_pack_type, type='char',
                                     string='Pack Type', readonly=True),
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
                                      readonly=True),
        'num_mantles': fields.function(_get_num_mantles,
                                       type='integer',
                                       string='Nº Mantles',
                                       readonly=True),
        'chained_loc_id': fields.many2one('stock.location',
                                          'Next Chained Location',
                                          help="Location where the products "
                                          "will be pushed to a specific "
                                          "location"),
        'task_id': fields.many2one('stock.task', 'In task', readonly=True),
        'to_process': fields.boolean('To process',
                                     help="When checked the operation will be\
                                     process when you finish task, else\
                                     will be unassigned"),
        # Used when aprovepackoperation2 on stock.picking, because this method
        # unlink the original operation and wee ned to remember it
        # In the scan_gun_warehouse module
        'old_id': fields.integer('Old id', readonly=True)

    }
    _defaults = {
        'to_process': True,
    }


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'ubication_type_id': fields.many2one('stock.picking.type',
                                             'Ubication Task Type'),
        'reposition_type_id': fields.many2one('stock.picking.type',
                                              'Reposition Task Type'),
        'max_volume': fields.float('Max. volume to move in picking',
                                   digits_compute=dp.get_precision
                                   ('Product Volume')),
    }


class stock_location(osv.Model):
    _inherit = 'stock.location'

    def _get_location_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for loc in self.browse(cr, uid, ids, context=context):
            res[loc.id] = loc.width * loc.height * loc.length
        return res

    def _get_quants_volume(self, cr, uid, quant_ids, context=None):
        """
        Function that return the total volume of quant_ids, gruping the
        packages in order to find the corect volume of var_palets.
        Palets or Var palets returns a volume by his number of mantles inside
        because when you quit some product from a palet, we discount the volume
        mantle by mantle.
        """
        t_quant = self.pool.get('stock.quant')
        t_pack = self.pool.get('stock.quant.package')
        if context is None:
            context = {}
        volume = 0.0
        pack_ids = set()

        for quant in t_quant.browse(cr, uid, quant_ids, context=context):
            if quant.package_id and quant.package_id.pack_type:
                pack_ids.add(quant.package_id.id)
            else:
                volume += quant.product_id.un_width * \
                    quant.product_id.un_height * \
                    quant.product_id.un_length * \
                    quant.qty
        pack_ids = list(pack_ids)
        for pack in t_pack.browse(cr, uid, pack_ids, context=context):
            net_qty = 0
            for quant in pack.quant_ids:
                net_qty += quant.qty
            if net_qty:
                volume += pack.volume
        return volume

    def _get_volume_for(self, pack, prop_qty, product, picking_zone=False):
        volume = 0.0
        un_ca = product.un_ca
        ca_ma = product.ca_ma
        mantle_units = un_ca * ca_ma
        if pack == 'palet':
            # num_mant = prop_qty // mantle_units
            num_mant = math.ceil(prop_qty / mantle_units)
            width_wood = product.pa_width
            length_wood = product.pa_length
            height_mant = product.ma_height
            wood_height = product.palet_wood_height
            if picking_zone:
                wood_height = 0  # No wood in picking location
            height_var_pal = (num_mant * height_mant) + wood_height
            volume = width_wood * length_wood * height_var_pal

        elif pack == "box":
            volume = product.ca_width * product.ca_height * product.ca_length
        elif pack == "units":
            volume = product.un_width * product.un_height * product.un_length \
                * prop_qty
        return volume

    def _get_available_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for id in ids:
            res[id] = {'available_volume': 0.0, 'filled_percent': 0.0}
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        t_prod = self.pool.get('product.product')
        for loc in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            quant_ids = quant_obj.search(cr, uid, [('location_id', '=',
                                                    loc.id)],
                                         context=context)
            volume = self._get_quants_volume(cr, uid, quant_ids,
                                             context=context)
            domain = [
                '|',
                ('location_dest_id', '=', loc.id),
                ('chained_loc_id', '=', loc.id),
                ('processed', '=', 'false'),
                ('picking_id.state', 'in', ['assigned'])
            ]
            operation_ids = ope_obj.search(cr, uid, domain, context=context)

            ops_by_pack = {}
            is_pick_zone = loc.zone == 'picking'
            for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
                # Operation Beach to input
                if not ope.package_id and ope.result_package_id:
                    pack = ope.result_package_id
                    if pack not in ops_by_pack:
                        ops_by_pack[ope.result_package_id] = [ope]
                    else:
                        ops_by_pack[ope.result_package_id].append(ope)
                # Location task operations or reposition
                elif ope.package_id and not ope.result_package_id:
                    pack_obj = ope.package_id
                    if is_pick_zone:
                        pack_obj = ope.package_id.with_context(no_wood=True)
                    volume += pack_obj.volume
                # Reposition operations
                elif ope.package_id and ope.result_package_id:
                    volume += \
                        self._get_volume_for(ope.result_package_id.pack_type,
                                             ope.product_qty,
                                             ope.product_id,
                                             picking_zone=True)
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
                    mantle_units = product.un_ca * product.ca_ma
                    num_mantles = int(math.ceil(qty / mantle_units))
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
                    width_wood = prod_obj.pa_width
                    length_wood = prod_obj.pa_length
                    height_wood = prod_obj.palet_wood_height
                    wood_volume = width_wood * length_wood * height_wood

                    volume += wood_volume

            res[loc.id]['available_volume'] = loc.volume - volume
            fill_per = loc.volume and volume * 100.0 / loc.volume or 0.0
            res[loc.id]['filled_percent'] = fill_per
        return res

    def _search_available_volume(self, cr, uid, obj, name, args, context=None):
        """ Function search to use available volume like a filter """
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

    def _get_filter_percentage(self, cr, uid, ids, name, args, context=None):
        """ Function search to use filled % like a filter. """
        if context is None:
            context = {}
        res = {}
        for loc in self.browse(cr, uid, ids, context=context):
            res[loc.id] = 'cualquier_cosa'
        return res

    def _search_filter_percent(self, cr, uid, obj, name, args, context=None):
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
        if context is None:
            context = {}
        res = {}
        for loc in self.browse(cr, uid, ids, context=context):
            res[loc.id] = 'cualquier_cosa'
        return res

    def _search_filter_aval(self, cr, uid, obj, name, args, context=None):
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
                    ('picking_id.state', 'in', ['assigned'])
                ]
                operation_ids = ope_obj.search(cr, uid, domain, limit=1,
                                               context=context)
                if operation_ids:
                    res[loc.id] = ope_obj.browse(cr, uid, operation_ids[0],
                                                 context=context).\
                        operation_product_id.id
        return res

    _order = 'sequence'
    _columns = {
        'width': fields.
        float('Width', digits_compute=dp.get_precision('Product Price')),
        'height': fields.
        float('Height', digits_compute=dp.get_precision('Product Price')),
        'length': fields.
        float('Lenght', digits_compute=dp.get_precision('Product Price')),
        'volume': fields.
        function(_get_location_volume, readonly=True, string='Volume',
                 type="float",
                 digits_compute=dp.get_precision('Product Volume')),
        'available_volume': fields.
        function(_get_available_volume, readonly=True, type="float",
                 string="Available volume",
                 digits_compute=dp.get_precision('Product Volume'),
                 fnct_search=_search_available_volume,
                 multi='mult'),
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
        'storage_type': fields.selection([('standard', 'Standard'),
                                         ('boxes', 'Boxes')],
                                         'Storage Type'),
        'current_product_id': fields.function(_get_current_product_id,
                                              string="Product",
                                              readonly=True,
                                              type="many2one",
                                              relation="product.product"),
        'temp_type_id': fields.many2one('temp.type', 'Temperature Type'),
        'sequence': fields.integer('Sequence', required=True),
        'camera': fields.boolean('Picking Camera',
                                 help="If True we can do picking of "
                                 "this location and childrens"),
        'zone': fields.selection([('storage', 'Storage Zone'),
                                  ('picking', 'Picking Zone')],
                                 'Location Zone'),
    }

    _defaults = {
        'storage_type': 'standard',
        'sequence': 0
    }

    def get_camera(self, cr, uid, ids, context=None):
        """
        Get the first parent location marked as camera.
        """
        res = False
        loc_id = ids[0]
        loc = self.browse(cr, uid, loc_id, context=context)
        while not res and loc.location_id:
            if loc.location_id.camera:
                res = loc.location_id.id
            else:
                loc = loc.location_id
        return res

    def get_locations_by_zone(self, cr, uid, ids, zone, add_domain=False,
                              context=None):
        """
        Get the camera from the loc_id and get the children locations of
        specified zone ('storage', 'picking')
        """
        locations = []
        loc_id = ids[0]
        if context is None:
            context = {'operation': 'greater'}
        ctx = context.copy()
        if zone not in ['picking', 'storage']:
            raise osv.except_osv(_('Error!'), _('Zone not exist.'))

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
        loc_id = False
        loc_id = ids[0]
        if context is None:
            context = {}
        if zone not in ['picking', 'storage']:
            raise osv.except_osv(_('Error!'), _('Zone %s not exist.') % zone)
        loc_camera_id = self.get_camera(cr, uid, [loc_id], context=context)
        if loc_camera_id:
            domain = [('location_id', '=', loc_camera_id),
                      ('zone', '=', zone)]
            locations = self.search(cr, uid, domain, context=context)
            loc_id = locations and locations[0] or False
        if not loc_id:
            cam = self.browse(cr, uid, loc_camera_id, context).name
            raise osv.except_osv(_('Error!'), _('No general %s location \
                                                 founded in camera %s.') %
                                 (zone, cam))

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
        return super(stock_location, self).search(cr, uid, args,
                                                  offset=offset,
                                                  limit=limit,
                                                  order=order,
                                                  context=context,
                                                  count=count)

    def name_search(self, cr, uid, name,
                    args=None, operator='ilike', context=None, limit=80):
        """
        Redefine the search to search by company name.
        """
        if context.get('search_product_id', False):
            loc_ids = self.search(cr, uid, args, context=context)
            args = [('id', 'in', loc_ids)]
        res = super(stock_location, self).name_search(cr, uid, name, args=args,
                                                      operator=operator,
                                                      limit=limit)
        return res


class stock_move(osv.osv):
    _inherit = "stock.move"

    _columns = {
        'trans_route_id': fields.related('procurement_id', 'trans_route_id',
                                         readonly=True,
                                         string='Transport Route',
                                         relation="route",
                                         type="many2one"),
        'route_detail_id': fields.related('procurement_id', 'route_detail_id',
                                          readonly=True,
                                          string='Detail Route',
                                          relation="route.detail",
                                          type="many2one"),
        # 'drop_code': fields.related('procurement_id', 'drop_code',
        #                             string="Drop Code",
        #                             type='integer', readonly=True),
        'real_weight': fields.float('Real weight'),
        'price_kg': fields.float('Price Kg'),
    }

    def _prepare_procurement_from_move(self, cr, uid, move, context=None):
        res = super(stock_move, self).\
            _prepare_procurement_from_move(cr, uid, move, context=context)
        route_detail_id = move.route_detail_id and move.route_detail_id.id or \
            False
        res['route_detail_id'] = route_detail_id
        # res['drop_code'] = move.drop_code
        return res

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False):
        """
        Get the price_kg of the product
        """
        res = super(stock_move, self)\
            .onchange_product_id(cr, uid, ids, prod_id=prod_id, loc_id=loc_id,
                                 loc_dest_id=loc_dest_id,
                                 partner_id=partner_id)
        if not prod_id:
            return {}
        product = self.pool.get('product.product').browse(cr, uid,
                                                          [prod_id])[0]
        res['value']['price_kg'] = product.price_kg
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(stock_move, self).write(cr, uid, ids, vals,
                                            context=context)
        # para arrastrar la ruta al albaran desde la venta
        if vals.get('picking_id', False):
            pick_obj = self.pool.get('stock.picking')
            proc_obj = self.pool.get('procurement.order')
            for move in self.browse(cr, uid, ids, context=context):
                procurement = False
                if vals.get('procurement_id', False):
                    procurement = vals['procurement_id']
                else:
                    procurement = move.procurement_id and \
                        move.procurement_id.id or False

                if procurement:
                    procurement = proc_obj.browse(cr, uid, procurement,
                                                  context=context)
                    if procurement.route_detail_id:
                        vls = {'route_detail_id':
                               procurement.route_detail_id.id}
                        pick_obj.write(cr, uid, vals['picking_id'], vls,
                                       context=context)
        if vals.get('real_weight', False):
            t_uom = self.pool.get('product.uom')
            real_weight = vals['real_weight']
            if real_weight:
                uom_ids = t_uom.search(cr, uid, [('like_type', '=', 'kg')])
                if uom_ids:
                    vals = {
                        'product_uos': uom_ids[0],
                        'product_uos_qty': real_weight
                    }
                    self.write(cr, uid, ids, vals, context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        if vals.get('real_weight', False):
            t_uom = self.pool.get('product.uom')
            real_weight = vals['real_weight']
            if real_weight:
                uom_ids = t_uom.search(cr, uid, [('like_type', '=', 'kg')])
                if uom_ids:
                    vals2 = {
                        'product_uos': uom_ids[0],
                        'product_uos_qty': real_weight
                    }
                    vals.update(vals2)
        res = super(stock_move, self).create(cr, uid, vals, context=context)
        return res

    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type,
                               context=None):
        """
        Add to invoice the price_kg of product and a link to the move in order
        to know the sale_orders and pickings from invoice.
        """
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move,
                                                             partner, inv_type,
                                                             context=context)
        if move.real_weight:
            res['price_unit'] = move.price_kg
        res.update({'stock_move_id': move.id})
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


class stock_inventory(osv.osv):

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
                                   required=True),
    }

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


class stock_picking_wave(osv.osv):
    _inherit = "stock.picking.wave"

    _columns = {
        'wave_report_ids': fields.one2many('wave.report', 'wave_id',
                                           'Picking Report', readonly=True),
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
                                      readonly=True),
    }


class stock_quant(osv.osv):
    _inherit = 'stock.quant'

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
        t_location = self.pool.get('stock.location')
        # When quants already assigned we use the super no midban depot fefo
        already_reserved = False
        for x in domain:
            if x[0] == 'reservation_id' and x[2]:
                already_reserved = True
                removal_strategy = 'fefo'
        if removal_strategy == 'depot_fefo' and not already_reserved and not \
                ('force_quants_location' in context):
            pick_loc_obj = product.picking_location_id
            if not pick_loc_obj:
                raise osv.except_osv(_('Error!'), _('Not picking location\
                                        defined for product %s') %
                                     product.name)
            order = 'removal_date, in_date, id'
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
            return res
        elif context.get('force_quants_location', False):
            # domain.append(('location_id', '=', location.id))
            # res = self._quants_get_order(cr, uid, location, product, qty,
            #                              domain, context=context)
            res = context['force_quants_location']
            if not res:
                raise osv.except_osv(_('Error!'), _('No quants to force the \
                                                    assignament'))
            return res
        sup = super(stock_quant, self).\
            apply_removal_strategy(cr, uid, location, product, qty, domain,
                                   removal_strategy, context=context)
        return sup


class stock_location_rule(osv.osv):
    _inherit = "stock.location.route"

    _columns = {
        'cross_dock': fields.boolean('Cross Dock Route',
                                     help="mark to avoid stock virtual"
                                     "conservative warning"),
    }


class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
        'customer_ids': fields.many2many('res.partner', 'customers_lot_rel',
                                         'lot_id', 'partner_id',
                                         'Related customers',
                                         domain=[('customer', '=', True)]),
        'supplier_ids': fields.many2many('res.partner', 'supplier_lot_rel',
                                         'lot_id', 'partner_id',
                                         'Related suppliers',
                                         domain=[('supplier', '=', True)])
    }

###############################################################################
###############################################################################


class stock_config_settings(models.TransientModel):
    # _name = 'stock.config.settings'
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
