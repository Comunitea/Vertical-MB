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
        'route_id': fields.many2one('route', 'Transport Route', readonly=True),
        'drop_code': fields.integer('Drop Code', readonly=True),
        'midban_operations': fields.boolean("Exist midban operation"),
    }

    @api.cr_uid_ids_context
    def approve_pack_operations(self, cr, uid, ids, context=None):
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
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.move_lines and pick.move_lines[0].move_dest_id:
                related_pick_id = pick.move_lines[0].move_dest_id.picking_id.id
                self.do_prepare_partial(cr, uid, [related_pick_id],
                                        context=context)
                self.write(cr, uid, [related_pick_id],
                           {'midban_operations': True}, context=context)
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
                pack_type = pack.pack_type
                # if pack_type in ['palet', 'var_palet'] and pack.product_id:
                if pack_type == 'palet' and pack.product_id:
                    units_in_mantle = pack.product_id.supplier_un_ca * \
                        pack.product_id.supplier_ca_ma
                    if units_in_mantle:
                        mantles = math.ceil(pack.packed_qty / units_in_mantle)
            res[pack.id] = mantles
        return res

    def _get_pack_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        t_loc = self.pool.get('stock.location')
        t_whs = self.pool.get('stock.warehouse')
        for pack in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            if pack.product_id:
                prod = pack.product_id
                whs_id = t_loc.get_warehouse(cr, uid, pack.location_id,
                                             context=context)
                warehouse = t_whs.browse(cr, uid, whs_id, context=context)
                picking_loc_id = warehouse.picking_loc_id.id
                loc_dest_obj = t_loc.browse(cr, uid, pack.location_id.id,
                                            context=context)
                parent_loc_id = loc_dest_obj.location_id.id
                if pack.pack_type:  # Get volume of box,palet or var_palet
                    if pack.pack_type == 'box':
                        volume = prod.supplier_ca_width * \
                            prod.supplier_ca_height * prod.supplier_ca_length
                    # elif pack.pack_type in ['palet', 'var_palet']:
                    elif pack.pack_type == 'palet':
                        num_mant = pack.num_mantles
                        width_wood = prod.supplier_pa_width
                        length_wood = prod.supplier_pa_length
                        height_mant = prod.supplier_ma_height
                        wood_height = prod.palet_wood_height
                        if parent_loc_id == picking_loc_id:
                            wood_height = 0  # No wood in picking location
                        height_var_pal = (num_mant * height_mant) + wood_height
                        volume = width_wood * length_wood * height_var_pal
                if not volume:  # Get volume of individual units
                    volume = pack.product_id.supplier_un_width * \
                        pack.product_id.supplier_un_height * \
                        pack.product_id.supplier_un_length * \
                        pack.packed_qty
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
                                      digits_compute=
                                      dp.get_precision('Product Price'),),
        'num_mantles': fields.function(_get_pack_mantles,
                                       type="integer",
                                       string="Nº mantles",
                                       readonly=True,),
        'volume': fields.function(_get_pack_volume, readonly=True,
                                  type="float",
                                  string="Volume",
                                  digits_compute=
                                  dp.get_precision('Product Volume')),
    }


class stock_pack_operation(osv.osv):
    _inherit = "stock.pack.operation"

    def _search_closest_pick_location(self, cr, uid, prod_obj,
                                      free_loc_ids, context=None):
        if context is None:
            context = {}
        if not free_loc_ids:
            raise osv.except_osv(_('Error!'), _('No empty locations.'))

        names = []
        loc_names = []
        loc_t = self.pool.get('stock.location')
        for loc in loc_t.browse(cr, uid, free_loc_ids, context):
            names.append(loc.name)
        names.append(prod_obj.picking_location_id.name)
        loc_names = sorted(names)
        i = loc_names.index(prod_obj.picking_location_id.name)
        # TODO MEJORAR INTELIGENCIA, COMPARADOR UBICACIONES
        if i == len(free_loc_ids):
            i = i - 1
        return free_loc_ids[i]

    def _older_refernce_in_storage(self, cr, uid, product, wh_obj,
                                   context=None):
        if context is None:
            context = {}
        res = False
        t_quant = self.pool.get("stock.quant")
        domain = [
            ('company_id', '=', wh_obj.company_id.id),
            ('product_id', '=', product.id),
            ('qty', '>', 0),
            ('location_id', 'child_of', [wh_obj.storage_loc_id.id]),
        ]
        quant_ids = t_quant.search(cr, uid, domain, context=context)
        if quant_ids:
            res = True
        return res

    def _get_location(self, cr, uid, ops, wh_obj, context=None):
        """
        For a product, choose between put it in picking zone (if it is empty
        and no older reference stored in storage zone or put it in closest
        storage zone to product picking location
        """
        if context is None:
            context = {}
        location_id = False
        loc_obj = self.pool.get('stock.location')
        storage_id = wh_obj.storage_loc_id.id
        if (ops.operation_product_id and
                ops.operation_product_id.picking_location_id):
            product = ops.operation_product_id
            pick_loc = ops.operation_product_id.picking_location_id
            old_ref = self._older_refernce_in_storage(cr, uid, product, wh_obj,
                                                      context=context)
            if not pick_loc.filled_percent:  # If empty add wood volume
                width_wood = product.supplier_pa_width
                length_wood = product.supplier_pa_length
                height_wood = product.palet_wood_height
                wood_volume = width_wood * length_wood * height_wood
                vol_aval = pick_loc.available_volume - wood_volume
            else:
                vol_aval = pick_loc.available_volume
            if (not old_ref and ops.volume <= vol_aval) or \
                    not ops.package_id:  # Only units forced going to picking
                location_id = pick_loc.id
            else:
                loc_type = "standard"
                if ops.pack_type and ops.pack_type == 'box':
                    loc_type = "boxes"
                temp_type = product.temp_type and product.temp_type.id or False
                if loc_type:
                    loc_ids = loc_obj.search(cr, uid,
                                             [('storage_type', '=', loc_type),
                                              ('temp_type_id', '=', temp_type),
                                              ('location_id', 'child_of',
                                               [storage_id])],
                                             context=context)
                    free_locs = []
                    # Remove Storage location from the list
                    if loc_ids and storage_id in loc_ids:
                        loc_ids.remove(storage_id)
                    for loc in loc_obj.browse(cr, uid, loc_ids,
                                              context=context):
                        condition = True
                        if ops.pack_type == 'palet':
                            condition = not loc.current_product_id
                        if condition and loc.available_volume >= ops.volume:
                            free_locs.append(loc.id)

                    location_id = self.\
                        _search_closest_pick_location(cr, uid, product,
                                                      free_locs,
                                                      context=context)

        return location_id

    def change_location_dest_id(self, cr, uid, ids, wh_obj,
                                context=None):
        """
        Change the storage location for a specific one
        """
        if context is None:
            context = {}
        res = {}
        for op_id in ids:
            ops = self.browse(cr, uid, op_id, context=context)
            prod_obj = False
            if ops.package_id:
                for quant in ops.package_id.quant_ids:
                    if prod_obj and prod_obj.id != quant.product_id.id:
                        msg = 'Can not manage packages with different products'
                        raise osv.except_osv(_('Error!'), _(msg))
                    else:
                        prod_obj = quant.product_id
            else:
                prod_obj = ops.product_id and ops.product_id or False
            if not prod_obj:
                raise osv.except_osv(_('Error!'), _('No product founded\
                                                    inside package'))
            location_id = self._get_location(cr, uid, ops, wh_obj,
                                             context=context)
            if location_id:
                ops.write({'location_dest_id': location_id})

        return res

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

    def _get_operation_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        t_loc = self.pool.get('stock.location')
        t_whs = self.pool.get('stock.warehouse')
        for ope in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            whs_id = t_loc.get_warehouse(cr, uid, ope.location_dest_id,
                                         context=context)
            warehouse = t_whs.browse(cr, uid, whs_id, context=context)
            picking_loc_id = warehouse.picking_loc_id.id
            loc_dest_obj = t_loc.browse(cr, uid, ope.location_dest_id.id,
                                        context=context)
            parent_loc_id = loc_dest_obj.location_id.id
            if ope.pack_type:
                if ope.pack_type == "palet":
                    num_mant = ope.package_id.num_mantles
                    width_wood = ope.operation_product_id.supplier_pa_width
                    length_wood = ope.operation_product_id.supplier_pa_length
                    height_mant = ope.operation_product_id.supplier_ma_height
                    wood_height = ope.operation_product_id.palet_wood_height
                    if parent_loc_id == picking_loc_id:
                        wood_height = 0  # No wood in picking location
                    height_var_pal = (num_mant * height_mant) + wood_height
                    volume = width_wood * length_wood * height_var_pal

                elif ope.pack_type == "box":
                    volume = ope.operation_product_id.supplier_ca_width * \
                        ope.operation_product_id.supplier_ca_height * \
                        ope.operation_product_id.supplier_ca_length
            else:
                volume = ope.operation_product_id.supplier_un_width * \
                    ope.operation_product_id.supplier_un_height * \
                    ope.operation_product_id.supplier_un_length * \
                    ope.product_qty
            res[ope.id] = volume
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
                res[ope.id] = ope.package_id.num_mantles
            elif ope.product_id and ope.product_qty:
                un_ca = ope.product_id.supplier_un_ca
                ca_ma = ope.product_id.supplier_ca_ma
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
        'volume': fields.
        function(_get_operation_volume, readonly=True, type="float",
                 string="Volume",
                 digits_compute=dp.get_precision('Product Volume')),
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
    }


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'storage_loc_id': fields.many2one('stock.location',
                                          'Storage Location'),
        'picking_loc_id': fields.many2one('stock.location',
                                          'Picking Location'),
        'ubication_type_id': fields.many2one('stock.picking.type',
                                             'Ubication Task Type'),
        'reposition_type_id': fields.many2one('stock.picking.type',
                                              'Reposition Task Type'),
        # 'min_boxes_move': fields.integer('Min. boxes to move in picking'),
        # 'max_boxes_move': fields.integer('Max. boxes to move in picking'),
        'max_volume': fields.float('Max. volume to move in picking',
                                   digits_compute=
                                   dp.get_precision('Product Volume')),
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
                volume += quant.product_id.supplier_un_width * \
                    quant.product_id.supplier_un_height * \
                    quant.product_id.supplier_un_length * \
                    quant.qty
        pack_ids = list(pack_ids)
        for pack in t_pack.browse(cr, uid, pack_ids, context=context):
            volume += pack.volume
        return volume

    def _get_available_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        wh_obj = self.pool.get('stock.warehouse')
        t_prod = self.pool.get('product.product')
        for loc in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            quant_ids = quant_obj.search(cr, uid, [('location_id', '=',
                                                    loc.id)],
                                         context=context)
            volume = self._get_quants_volume(cr, uid, quant_ids,
                                             context=context)

            domain = [
                ('location_dest_id', '=', loc.id),
                ('processed', '=', 'false'),
                ('picking_id.state', 'in', ['assigned'])
            ]
            operation_ids = ope_obj.search(cr, uid, domain, context=context)
            for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
                volume += ope.volume

            whs_id = self.get_warehouse(cr, uid, loc, context=context)
            warehouse = wh_obj.browse(cr, uid, whs_id, context=context)
            picking_loc_id = warehouse.picking_loc_id.id
            cond1 = loc.location_id and loc.location_id.id == picking_loc_id
            cond2 = quant_ids or operation_ids
            if cond1 and cond2:
                 # Add wood volume, only one wood
                prod_id = t_prod.search(cr, uid,
                                        [('picking_location_id', '=', loc.id)],
                                        context=context, limit=1)
                if prod_id:
                    prod_obj = t_prod.browse(cr, uid, prod_id, context=context)
                    width_wood = prod_obj.supplier_pa_width
                    length_wood = prod_obj.supplier_pa_length
                    height_wood = prod_obj.palet_wood_height
                    wood_volume = width_wood * length_wood * height_wood

                    volume += wood_volume

            res[loc.id] = loc.volume - volume

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

    def _get_filled_percentage(self, cr, uid, ids, name, args, context=None):
        """ Function search to use filled % like a filter. """
        if context is None:
            context = {}
        res = {}
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        wh_obj = self.pool.get('stock.warehouse')
        t_prod = self.pool.get('product.product')
        for loc in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            quant_ids = quant_obj.search(cr, uid, [('location_id', '=',
                                                    loc.id)],
                                         context=context)
            volume = self._get_quants_volume(cr, uid, quant_ids,
                                             context=context)

            domain = [
                ('location_dest_id', '=', loc.id),
                ('processed', '=', 'false'),
                ('picking_id.state', 'in', ['assigned'])

            ]
            operation_ids = ope_obj.search(cr, uid, domain, context=context)
            for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
                volume += ope.volume

            whs_id = self.get_warehouse(cr, uid, loc, context=context)
            warehouse = wh_obj.browse(cr, uid, whs_id, context=context)
            picking_loc_id = warehouse.picking_loc_id.id
            cond1 = loc.location_id and loc.location_id.id == picking_loc_id
            cond2 = quant_ids or operation_ids
            if cond1 and cond2:
                 # Add wood volume. Only one wood
                prod_id = t_prod.search(cr, uid,
                                        [('picking_location_id', '=', loc.id)],
                                        context=context, limit=1)
                if prod_id:
                    prod_obj = t_prod.browse(cr, uid, prod_id, context=context)
                    width_wood = prod_obj.supplier_pa_width
                    length_wood = prod_obj.supplier_pa_length
                    height_wood = prod_obj.palet_wood_height
                    wood_volume = width_wood * length_wood * height_wood

                    volume += wood_volume
            res[loc.id] = loc.volume and ((volume * 100) / loc.volume) or 0.0
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
                 fnct_search=_search_available_volume),
        'filter_available': fields.function(_get_filter_available,
                                            type="char",
                                            string="Available Between X-Y",
                                            fnct_search=_search_filter_aval),
        'filled_percent': fields.function(_get_filled_percentage, type="float",
                                          string="Filled %",
                                          digits_compute=
                                          dp.get_precision('Product Price'),
                                          fnct_search=_search_filled_percent),
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
        'sequence': fields.integer('Sequence', required=True)
    }

    _defaults = {
        'storage_type': 'standard',
        'sequence': 0
    }


class procurement_order(osv.osv):
    _inherit = "procurement.order"

    _columns = {
        'route_id': fields.many2one('route', 'Transport Route',
                                    domain=[('state', '=', 'active')]),
    }


class stock_move(osv.osv):
    _inherit = "stock.move"

    _columns = {
        'route_id': fields.related('procurement_id', 'route_id', readonly=True,
                                   string='Transport Route', relation="route",
                                   type="many2one"),
        'real_weight': fields.float('Real weight'),
    }

    def _prepare_procurement_from_move(self, cr, uid, move, context=None):
        res = super(stock_move, self).\
            _prepare_procurement_from_move(cr, uid, move, context=context)
        res['route_id'] = move.route_id.id
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res = super(stock_move, self).write(cr, uid, ids, vals,
                                            context=context)

        if vals.get('picking_id', False):
            pick_obj = self.pool.get('stock.picking')
            proc_obj = self.pool.get('procurement.order')
            for move in self.browse(cr, uid, ids, context=context):
                procurement = False
                if vals.get('procurement_id', False):
                    procurement = vals['procurement_id']
                else:
                    procurement = move.procurement_id.id

                if procurement:
                    procurement = proc_obj.browse(cr, uid, procurement,
                                                  context=context)
                    if procurement.route_id:
                        pick_obj.write(cr, uid, vals['picking_id'],
                                       {'route_id': procurement.route_id.id},
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
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move,
                                                             partner, inv_type,
                                                             context=context)
        if move.real_weight:
            res['price_unit'] = move.product_id.price_kg
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
                                           'Picking List', readonly=True),
        'temp_id': fields.many2one('temp.type', 'Temperature'),
        'route_id': fields.many2one('route', 'Transport Route',
                                    domain=[('state', '=', 'active')]),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
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
        t_warehouse = self.pool.get('stock.warehouse')

        if removal_strategy == 'depot_fefo':
            order = 'removal_date, in_date, id'

            res = self._quants_get_order(cr, uid, location, product, qty,
                                         domain, order, context=context)
            check_storage_qty = 0.0
            for record in res:
                if record[0] is None:
                    check_storage_qty += record[1]
                    res.remove(record)
            wh_id = t_location.get_warehouse(cr, uid, location,
                                             context=context)
            wh_obj = t_warehouse.browse(cr, uid, wh_id, context=context)
            storage_id = wh_obj.storage_loc_id.id
            storage_loc = storage_id and \
                t_location.browse(cr, uid, storage_id) or False

            # Search quants in storage location
            domain = [('reservation_id', '=', False), ('qty', '>', 0)]
            if check_storage_qty and storage_loc:
                res += self._quants_get_order(cr, uid, storage_loc, product,
                                              check_storage_qty, domain, order,
                                              context=context)
            return res
        sup = super(stock_quant, self).\
            apply_removal_strategy(cr, uid, location, product, qty, domain,
                                   removal_strategy, context=context)
        return sup
