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
from openerp.osv import osv, fields
from openerp import api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


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
        # 'reposition': fields.boolean('Reposition', readonly=True),
    }

    def _get_unit_conversions(self, cr, uid, ids, op_obj, context=None):
        """
        Get a op line obj. Returns a dict with op line qty converted in
        units, boxes, mantles and paletes.
        """
        res = {
            'units': 0.0,
            'boxes': 0.0,
            'mantles': 0.0,
            'palets': 0.0,
        }
        unit_type = op_obj.product_uom_id.like_type or 'units'
        un_ca = op_obj.product_id.supplier_un_ca
        ca_ma = op_obj.product_id.supplier_ca_ma
        ma_pa = op_obj.product_id.supplier_ma_pa
        qty = op_obj.product_qty
        if unit_type == 'units':
            res['units'] = qty
            res['boxes'] = un_ca and (res['units'] / un_ca) or 0.0
            res['mantles'] = ca_ma and (res['boxes'] / ca_ma) or 0.0
            res['palets'] = ma_pa and (res['mantles'] / ma_pa) or 0.0
        elif unit_type == 'boxes':
            res['units'] = un_ca and (qty * un_ca, 2) or 0.0
            res['boxes'] = qty
            res['mantles'] = ca_ma and (res['boxes'] / ca_ma) or 0.0
            res['palets'] = ma_pa and (res['mantles'] / ma_pa) or 0.0
        elif unit_type == 'mantles':
            res['units'] = un_ca and (res['boxes'] * un_ca) or 0.0
            res['boxes'] = ca_ma and (res['mantles'] * ca_ma) or 0.0
            res['mantles'] = qty
            res['palets'] = ma_pa and (res['mantles'] / ma_pa) or 0.0
        elif unit_type == 'palets':
            res['units'] = un_ca and (res['boxes'] * un_ca) or 0.0
            res['boxes'] = ca_ma and (res['mantles'] * ca_ma) or 0.0
            res['mantles'] = ma_pa and (res['palets'] * ma_pa) or 0.0
            res['palets'] = qty
        return res

    def _get_pack_type_operation(self, cr, uid, ids, op, pack_type, num,
                                 context=None):
        """
        Return a dictionary containing the values to create a pack operation
        with pack and his pack type setted when we can, or a operation without
        package in other case.
        """
        if context is None:
            context = {}
        res = []
        t_pack = self.pool.get('stock.quant.package')
        op_vals = {
            'location_id': op.location_id.id,
            'product_id': op.operation_product_id.id,
            'product_uom_id': (op.product_uom_id and op.product_uom_id.id or
                               op.operation_product_id.uom_id.id),
            'location_dest_id': op.location_dest_id.id,
            'picking_id': op.picking_id.id,
        }
        if pack_type not in ['palet', 'mantle', 'box']:
            op_vals.update({
                'product_qty': num,
            })
            res.append(op_vals)
        else:
            for n in range(num):
                ma_pa = op.product_id.supplier_ma_pa
                ca_ma = op.product_id.supplier_ca_ma
                un_ca = op.product_id.supplier_un_ca
                if pack_type == 'palet':
                    pack_units = ma_pa * ca_ma * un_ca
                    pack_name = 'PALET'
                elif pack_type == 'mantle':
                    pack_units = ca_ma * un_ca
                    pack_name = 'MANTO'
                elif pack_type == 'box':
                    pack_units = un_ca
                    pack_name = 'CAJA'
                package_id = t_pack.create(cr, uid, {'pack_type': pack_type},
                                           context=context)
                pack_obj = t_pack.browse(cr, uid, package_id, context=context)
                new_name = pack_obj.name.replace("PACK", pack_name)
                pack_obj.write({'name': new_name})
                op_vals.update({
                    'result_package_id': package_id,
                    'product_qty': pack_units,
                })
                res.append(dict(op_vals))
        return res

    def _propose_pack_operations(self, cr, uid, ids, op, context=None):
        """
        Return a list of vals in order to create new pack operations.
        The original operation is splited into several operations with the
        packs and pack types(palets, mantles, boxes) defined.
        """
        if context is None:
            context = {}
        res = []
        prod_obj = op.product_id
        conv = self._get_unit_conversions(cr, uid, ids, op, context)
        if conv['palets'] >= 1:
            palets = conv['palets']
            int_pal = int(palets)
            dec_pal = abs(palets) - abs(int(palets))
            pa_dics = self._get_pack_type_operation(cr, uid, ids, op, 'palet',
                                                    int_pal, context=context)
            res.extend(pa_dics)
            if dec_pal != 0:  # Get a integer number of mantles or boxes
                num_mant = prod_obj.supplier_ma_pa * dec_pal
                if num_mant >= 1:  # Get mantles and maybe some boxes
                    int_man = int(num_mant)
                    dec_man = abs(num_mant) - abs(int(num_mant))
                    ma_dics = self._get_pack_type_operation(cr, uid, ids, op,
                                                            'mantle', int_man,
                                                            context=context)
                    res.extend(ma_dics)
                    if dec_man != 0:  # Ubicate boxes
                        num_box = prod_obj.supplier_ca_ma * dec_man
                        if num_box >= 1:  # Get boxes and maybe some units
                            int_box = int(num_box)
                            dec_box = abs(num_box) - abs(int(num_box))
                            bo_dics = self.\
                                _get_pack_type_operation(cr, uid, ids, op,
                                                         'box', int_box,
                                                         context=context)
                            res.extend(bo_dics)
                            if dec_box != 0:  # Get operations for units
                                units = prod_obj.supplier_un_ca * dec_box
                                un_dic = self.\
                                    _get_pack_type_operation(cr, uid, ids, op,
                                                             'units', units,
                                                             context=context)
                                res.extend(un_dic)

                        else:  # ubicate the rest of units
                            units = prod_obj.supplier_un_ca * num_box
                            un_dics = self.\
                                _get_pack_type_operation(cr, uid, ids, op,
                                                         'units', units,
                                                         context=context)
                            res.extend(un_dics)
                else:  # Ubicate Boxes
                    num_box = prod_obj.supplier_ca_ma * num_mant
                    if num_box >= 1:  # Get boxes and maybe some units
                        int_box = int(num_box)
                        dec_box = abs(num_box) - abs(int(num_box))
                        bo_dics = self.\
                            _get_pack_type_operation(cr, uid, ids, op, 'box',
                                                     int_box, context=context)
                        res.extend(bo_dics)
                        if dec_box != 0:  # Get operations for units
                            units = prod_obj.supplier_un_ca * dec_box
                            un_dics = self.\
                                _get_pack_type_operation(cr, uid, ids, op,
                                                         'units', units,
                                                         context=context)
                            res.extend(un_dics)
                    else:  # Ubicate the rest of units
                        units = prod_obj.supplier_un_ca * num_box
                        un_dics = self.\
                            _get_pack_type_operation(cr, uid, ids, op,
                                                     'units', units,
                                                     context=context)
                        res.extend(un_dics)

        elif conv['mantles'] >= 1:
            mantles = conv['mantles']
            int_man = int(mantles)
            dec_man = abs(mantles) - abs(int(mantles))
            ma_dics = self._get_pack_type_operation(cr, uid, ids, op,
                                                    'mantle', int_man,
                                                    context=context)
            res.extend(ma_dics)
            if dec_man != 0:  # Ubicate boxes
                num_box = prod_obj.supplier_ca_ma * mantles
                if num_box >= 1:  # Get boxes and maybe some units
                    int_box = int(num_box)
                    dec_box = abs(num_box) - abs(int(num_box))
                    bo_dics = self.\
                        _get_pack_type_operation(cr, uid, ids, op, 'box',
                                                 int_box, context=context)
                    res.extend(bo_dics)
                    if dec_box != 0:  # Get operations for units
                        units = prod_obj.supplier_un_ca * dec_box
                        un_dics = self.\
                            _get_pack_type_operation(cr, uid, ids, op, 'units',
                                                     units, context=context)
                        res.extend(un_dics)

        elif conv['boxes'] > 0:
            boxes = conv['boxes']
            int_box = int(boxes)
            dec_box = abs(boxes) - abs(int(boxes))
            bo_dics = self._get_pack_type_operation(cr, uid, ids, op,
                                                    'box', int_box,
                                                    context=context)
            res.extend(bo_dics)
            if dec_box != 0:  # Get operations for units
                units = prod_obj.supplier_un_ca * dec_box
                un_dics = self._get_pack_type_operation(cr, uid, ids, op,
                                                        'units', units,
                                                        context=context)
                res.extend(un_dics)

        else:
            units = conv['units']
            un_dics = self._get_pack_type_operation(cr, uid, ids, op,
                                                    'units', units,
                                                    context=context)
            res.extend(un_dics)

        return res

    @api.cr_uid_ids_context
    def prepare_package_type_operations(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        t_pack_op = self.pool.get('stock.pack.operation')
        self.do_prepare_partial(cr, uid, ids, context=context)
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.picking_type_id.code == 'incoming':
                for op in pick.pack_operation_ids:
                    vals_ops = self._propose_pack_operations(cr, uid, ids, op,
                                                             context=context)
                    #  If val_ ops:
                    #  Indent to get default operations # TODO?
                    t_pack_op.unlink(cr, uid, [op.id], context=context)
                    for vals in vals_ops:  # Create proposed operations
                        t_pack_op.create(cr, uid, vals, context=context)
        return True

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
        return True


class stock_package(osv.osv):
    _inherit = "stock.quant.package"
    _columns = {
        'pack_type': fields.selection([('box', 'Box'), ('mantle', 'Mantle'),
                                       ('palet', 'Palet')], 'Pack Type',
                                      readonly=True),
        'product_id': fields.related('quant_ids', 'product_id', readonly=True,
                                     type="many2one", string="Product",
                                     relation="product.product")
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
        if i == len(free_loc_ids) - 1:
            i = i - 1
        return free_loc_ids[i]

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
            if (pick_loc.volume == pick_loc.available_volume and
                    ops.volume <= pick_loc.available_volume):
                location_id = pick_loc.id
            else:
                if ops.pack_type and ops.pack_type == 'box':
                    loc_type = "boxes"
                elif ops.pack_type:
                    loc_type = "standard"
                else:
                    loc_type = False

                if loc_type:
                    loc_ids = loc_obj.search(cr, uid,
                                             [('storage_type', '=', loc_type),
                                              ('location_id', 'child_of',
                                               [storage_id])],
                                             context=context)
                    free_locs = []
                    for loc in loc_obj.browse(cr, uid, loc_ids,
                                              context=context):
                        if ((not loc.current_product_id or
                             loc.current_product_id.id == product.id) and
                                loc.available_volume >= ops.volume):
                            free_locs.append(loc.id)

                    location_id = self.\
                        _search_closest_pick_location(cr, uid, product,
                                                      free_locs,
                                                      context=context)
                else:
                    # TODO: A donde van las unidades sueltas?????
                    location_id = False

        return location_id

    def change_location_dest_id(self, cr, uid, operations, wh_obj,
                                context=None):
        """
        Change the storage location for a specific one
        """
        if context is None:
            context = {}
        res = {}
        for ops in operations:
            ops = self.browse(cr, uid, ops.id, context=context)
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
        for ope in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            if ope.pack_type:
                if ope.pack_type == "palet":
                    volume = ope.operation_product_id.supplier_pa_width * \
                        (ope.operation_product_id.supplier_pa_height +
                         ope.operation_product_id.palet_wood_height) * \
                        ope.operation_product_id.supplier_pa_length
                elif ope.pack_type == "mantle":
                    volume = ope.operation_product_id.supplier_ma_width * \
                        (ope.operation_product_id.supplier_ma_height +
                         ope.operation_product_id.mantle_wood_height) * \
                        ope.operation_product_id.supplier_ma_length
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

    _columns = {
        'pack_type': fields.function(_get_pack_type, type='char',
                                     string='Pack Type', readonly=True),
        'volume': fields.
        function(_get_operation_volume, readonly=True, type="float",
                 string="Volume",
                 digits_compute=dp.get_precision('Product Price')),
        'operation_product_id': fields.function(_get_real_product,
                                                type="many2one",
                                                relation="product.product",
                                                readonly=True,
                                                string="Product")
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
        'picking_type_id': fields.many2one('stock.picking.type',
                                           'Picking Task Type'),
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

    def _get_available_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        for loc in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            quant_ids = quant_obj.search(cr, uid, [('location_id', '=',
                                                    loc.id)],
                                         context=context)
            for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
                volume += quant.volume

            operation_ids = ope_obj.search(cr, uid, [('location_dest_id', '=',
                                                      loc.id), ('processed',
                                                                '=',
                                                                'false')],
                                           context=context)
            for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
                volume += ope.volume

            res[loc.id] = loc.volume - volume

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
                operation_ids = ope_obj.search(cr, uid, [('location_dest_id',
                                                          '=', loc.id),
                                                         ('processed', '=',
                                                          'false')],
                                               context=context, limit=1)
                if operation_ids:
                    res[loc.id] = ope_obj.browse(cr, uid, operation_ids[0],
                                                 context=context).\
                        operation_product_id.id

        return res

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
                 digits_compute=dp.get_precision('Product Price')),
        'available_volume': fields.
        function(_get_available_volume, readonly=True, type="float",
                 string="Available volume",
                 digits_compute=dp.get_precision('Product Price')),
        'storage_type': fields.selection([('standard', 'Standard'),
                                         ('boxes', 'Boxes')],
                                         'Storage Type'),
        'current_product_id': fields.function(_get_current_product_id,
                                              string="Product",
                                              readonly=True,
                                              type="many2one",
                                              relation="product.product")
    }

    _defaults = {
        'storage_type': 'standard',
    }


class stock_quant(osv.Model):
    _inherit = "stock.quant"

    def _get_quant_volume(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for quant in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            if quant.package_id and quant.package_id.pack_type:
                if quant.package_id.pack_type == "palet":
                    volume = quant.product_id.supplier_pa_width * \
                        (quant.product_id.supplier_pa_height +
                         quant.product_id.palet_wood_height) * \
                        quant.product_id.supplier_pa_length
                elif quant.package_id.pack_type == "mantle":
                    volume = quant.product_id.supplier_ma_width * \
                        (quant.product_id.supplier_ma_height +
                         quant.product_id.mantle_wood_height) * \
                        quant.product_id.supplier_ma_length
                elif quant.package_id.pack_type == "box":
                    volume = quant.product_id.supplier_ca_width * \
                        quant.product_id.supplier_ca_height * \
                        quant.product_id.supplier_ca_length
            else:
                volume = quant.product_id.supplier_un_width * \
                    quant.product_id.supplier_un_height * \
                    quant.product_id.supplier_un_length * \
                    quant.qty

            res[quant.id] = volume

        return res

    _columns = {
        'volume': fields.
        function(_get_quant_volume, readonly=True, type="float",
                 string="Volume",
                 digits_compute=dp.get_precision('Product Price')),
    }


class product_putaway_strategy(osv.osv):
    _inherit = 'product.putaway'

    def _get_putaway_options(self, cr, uid, context=None):
        return [('product_pick_location', 'Product picking location')] + \
            super(product_putaway_strategy, self).\
            _get_putaway_options(cr, uid, context=context)

    def putaway_apply(self, cr, uid, putaway_strat, product, context=None):
        import ipdb; ipdb.set_trace()
        if putaway_strat.method == 'product_pick_location':
            return product.picking_location_id.id
        else:
            return super(product_putaway_strategy, self).\
                putaway_apply(cr, uid, putaway_strat, product, context=context)
