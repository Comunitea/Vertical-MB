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
from openerp import api
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
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                          readonly=True),
        'camera_ids': fields.many2many('stock.location',
                                       'pick_cameras_rel',
                                       'pick_id',
                                       'location_id',
                                       'Cameras picked',
                                       readonly=True),
        'midban_operations': fields.boolean("Exist midban operation"),
        'cross_dock': fields.boolean("From Cross Dock order"),
        'out_report_ids': fields.one2many('out.picking.report', 'picking_id',
                                          'Delivery List', readonly=True),
        # 'drop_code': fields.related('move_lines', 'procurement_id',
        #                             'drop_code', type="integer",
        #                             string="Drop Code",
        #                             readonly=True),
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
                # Get the correct ubication, changing each operation
                # for op in pick.pack_operation_ids:
                #     pack_id = op.result_package_id and op.result_package_id.id\
                #         or False
                #     op_vals = {
                #         'location_id': op.location_dest_id.id,
                #         'product_id': not pack_id and op.product_id.id
                #         or False,
                #         'product_qty': pack_id and 1 or op.product_qty,
                #         'product_uom_id': pack_id and False or
                #         op.product_uom_id.id,
                #         'location_dest_id': op.chained_loc_id.id,
                #         'chained_loc_id': False,
                #         'picking_id': related_pick_id,
                #         'lot_id': not pack_id and op.lot_id.id or False,
                #         'package_id': pack_id,
                #         'result_package_id': False}
                #     t_operation.create(cr, uid, op_vals, context=context)
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
        res = {}
        t_loc = self.pool.get('stock.location')
        # import ipdb; ipdb.set_trace()
        for pack in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            # if pack.product_id:
            #     prod = pack.product_id
            #     loc_dest_obj = t_loc.browse(cr, uid, pack.location_id.id,
            #                                 context=context)
            #     if pack.pack_type:  # Get volume of box,palet
            #         if pack.pack_type == 'box':
            #             volume = prod.ca_width * \
            #                 prod.ca_height * prod.ca_length
            #         # elif pack.pack_type in ['palet', 'var_palet']:
            #         elif pack.pack_type == 'palet':
            #             num_mant = pack.num_mantles
            #             width_wood = prod.pa_width
            #             length_wood = prod.pa_length
            #             height_mant = prod.ma_height
            #             wood_height = prod.palet_wood_height
            #             if loc_dest_obj.zone == 'picking':
            #                 wood_height = 0  # No wood in picking location
            #             height_var_pal = (num_mant * height_mant) + wood_height
            #             volume = width_wood * length_wood * height_var_pal
            #     if not volume:  # Get volume of individual units
            #         volume = pack.product_id.un_width * \
            #             pack.product_id.un_height * \
            #             pack.product_id.un_length * \
            #             pack.packed_qty
            # res[pack.id] = volume

            loc_dest_obj = t_loc.browse(cr, uid, pack.location_id.id,
                                        context=context)
            if pack.pack_type == 'box':  # No multiproduct
                prod = pack.product_id
                volume = prod.ca_width * prod.ca_height * prod.ca_length
            elif pack.pack_type == 'palet':  # Maybe multiproduct
                quants_by_prod = {}
                # Group quants inside the package by product
                for quant in pack.quant_ids:
                    product = quant.product_id
                    if product not in quants_by_prod:
                        quants_by_prod[product] = [quant]
                    else:
                        quants_by_prod[product].append(quant)

                # Get total height, grouping mantles by product
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
                if loc_dest_obj.zone == 'picking':
                    wood_height = 0
                sum_heights += wood_height  # Add wood height
                volume = width_wood * length_wood * sum_heights
            # else:  # Only units but I think never is the case. Not make sense
            #     volume = pack.product_id.un_width * \
            #         pack.product_id.un_height * \
            #          pack.product_id.un_length * \
            #          pack.packed_qty
            res[pack.id] = volume
        return res

    _columns = {
        'pack_type': fields.selection([('box', 'Box'),
                                       ('palet', 'Palet')],
                                      # ('var_palet', 'Var Palet')],
                                      'Pack Type',
                                      readonly=True),
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
    }


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

    # def _get_operation_volume(self, cr, uid, ids, name, args, context=None):
    #     if context is None:
    #         context = {}
    #     # import ipdb; ipdb.set_trace()
    #     res = {}
    #     t_loc = self.pool.get('stock.location')
    #     t_whs = self.pool.get('stock.warehouse')
    #     for ope in self.browse(cr, uid, ids, context=context):
    #         volume = 0.0
    #         whs_id = t_loc.get_warehouse(cr, uid, ope.location_dest_id,
    #                                      context=context)
    #         warehouse = t_whs.browse(cr, uid, whs_id, context=context)
    #         input_loc = warehouse.wh_input_stock_loc_id
    #         loc_dest_obj = t_loc.browse(cr, uid, ope.location_dest_id.id,
    #                                     context=context)
    #         # If goinf to input location, get volume for the chained location
    #         if loc_dest_obj.id == input_loc.id and ope.chained_loc_id:
    #             loc_dest_obj = ope.chained_loc_id
    #         if ope.pack_type:
    #             if ope.pack_type == "palet":
    #                 num_mant = ope.num_mantles
    #                 width_wood = ope.operation_product_id.pa_width
    #                 length_wood = ope.operation_product_id.pa_length
    #                 height_mant = ope.operation_product_id.ma_height
    #                 wood_height = ope.operation_product_id.palet_wood_height
    #                 if loc_dest_obj.zone == 'picking':
    #                     wood_height = 0  # No wood in picking location
    #                 height_var_pal = (num_mant * height_mant) + wood_height
    #                 volume = width_wood * length_wood * height_var_pal

    #             elif ope.pack_type == "box":
    #                 volume = ope.operation_product_id.ca_width * \
    #                     ope.operation_product_id.ca_height * \
    #                     ope.operation_product_id.ca_length
    #         else:
    #             volume = ope.operation_product_id.un_width * \
    #                 ope.operation_product_id.un_height * \
    #                 ope.operation_product_id.un_length * \
    #                 ope.product_qty
    #         res[ope.id] = volume
    #     return res

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
        # 'volume': fields.
        # function(_get_operation_volume, readonly=True, type="float",
        #          string="Volume",
        #          digits_compute=dp.get_precision('Product Volume')),
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
        # import ipdb; ipdb.set_trace()
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
            # for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
            #     volume += ope.volume
            ops_by_pack = {}
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
                    volume += ope.package_id.volume  # only monoproducts pack
                # Reposition operations
                elif ope.package_id and ope.result_package_id:
                    volume += \
                        self._get_volume_for(ope.result_package_id.pack_type,
                                             ope.product_qty,
                                             ope.product_id,
                                             pick_zone=True)
                # Units operations, no packages
                else:
                    volume += ope.operation_product_id.un_width * \
                        ope.operation_product_id.un_height * \
                        ope.operation_product_id.un_length * \
                        ope.product_qty

            cond1 = loc.zone == 'picking'
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
                if not cond1:
                    sum_heights += wood_height
                volume += width_wood * length_wood * sum_heights

            cond2 = quant_ids or ops_by_pack
            # Add wood volume, only one wood
            if cond1 and cond2:
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
        # import ipdb; ipdb.set_trace()
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


class stock_move(osv.osv):
    _inherit = "stock.move"

    _columns = {
        'trans_route_id': fields.related('procurement_id', 'trans_route_id',
                                         readonly=True,
                                         string='Transport Route',
                                         relation="route",
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
        route_id = move.trans_route_id and move.trans_route_id.id or False
        res['trans_route_id'] = route_id
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
                    if procurement.trans_route_id:
                        vls = {'trans_route_id': procurement.trans_route_id.id}
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
        """
        t_location = self.pool.get('stock.location')
        if removal_strategy == 'depot_fefo':
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
