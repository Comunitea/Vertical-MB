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
# import time


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
    _columns = {
        'pack_type': fields.selection([('box', 'Box'), ('mantle', 'Mantle'),
                                       ('palet', 'Palet'),
                                       ('var_palet', 'Var Palet')],
                                      'Pack Type',
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
            if (not old_ref and ops.volume <= pick_loc.available_volume):
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
                else:
                    # TODO: A donde van las unidades sueltas?????
                    location_id = False

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
        for ope in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            if ope.pack_type:
                if ope.pack_type == "palet":
                    volume = ope.operation_product_id.supplier_pa_width * \
                        (ope.operation_product_id.supplier_pa_height +
                         ope.operation_product_id.palet_wood_height) * \
                        ope.operation_product_id.supplier_pa_length
                elif ope.pack_type == "var_palet":
                    num_mant = len(ope.package_id.quant_ids)
                    width_wood = ope.operation_product_id.supplier_pa_width
                    length_wood = ope.operation_product_id.supplier_pa_length
                    height_mant = ope.operation_product_id.supplier_ma_height
                    wood_height = ope.operation_product_id.palet_wood_height
                    height_var_pal = (num_mant * height_mant) + wood_height
                    volume = width_wood * length_wood * height_var_pal

                elif ope.pack_type == "mantle":
                    volume = ope.operation_product_id.supplier_ma_width * \
                        ope.operation_product_id.supplier_ma_height * \
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
        'min_boxes_move': fields.integer('Min. boxes to move in picking'),
        'max_boxes_move': fields.integer('Max. boxes to move in picking')
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

            domain = [
                ('location_dest_id', '=', loc.id),
                ('processed', '=', 'false'),
                ('picking_id.state', 'in', ['assigned'])

            ]
            operation_ids = ope_obj.search(cr, uid, domain, context=context)
            for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
                volume += ope.volume

            res[loc.id] = loc.volume - volume
        return res

    def _search_available_volume(self, cr, uid, obj, name, args, context=None):
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

            domain = [
                ('location_dest_id', '=', loc.id),
                ('processed', '=', 'false'),
                ('picking_id.state', 'in', ['assigned'])

            ]
            operation_ids = ope_obj.search(cr, uid, domain, context=context)
            for ope in ope_obj.browse(cr, uid, operation_ids, context=context):
                volume += ope.volume

            res[loc.id] = loc.volume and ((volume * 100) / loc.volume) or 0.0
        return res

    def _search_filled_percent(self, cr, uid, obj, name, args, context=None):
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
                 digits_compute=dp.get_precision('Product Price'),
                 fnct_search=_search_available_volume),
        'filled_percent': fields.function(_get_filled_percentage, type="float",
                                          string="Filled %",
                                          digits_compute=
                                          dp.get_precision('Product Price'),
                                          fnct_search=_search_filled_percent),
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
                if quant.package_id.pack_type == "palet" and quant.qty == \
                    quant.product_id.supplier_ma_pa * \
                    quant.product_id.supplier_ca_ma * \
                        quant.product_id.supplier_un_ca:
                    volume = quant.product_id.supplier_pa_width * \
                        (quant.product_id.supplier_pa_height +
                         quant.product_id.palet_wood_height) * \
                        quant.product_id.supplier_pa_length
                elif quant.package_id.pack_type == "var_palet" and \
                    quant.qty == len(quant.package_id.quant_ids) * \
                    quant.product_id.supplier_ca_ma * \
                        quant.product_id.supplier_un_ca:
                        num_mant = len(quant.package_id.quant_ids)
                        width_wood = quant.product_id.supplier_pa_width
                        length_wood = quant.product_id.supplier_pa_length

                        height_mant = quant.product_id.supplier_ma_height
                        wood_height = quant.product_id.palet_wood_height
                        height_var_pal = (num_mant * height_mant) + wood_height

                        volume = width_wood * length_wood * height_var_pal

                elif quant.package_id.pack_type == "mantle" and quant.qty == \
                    quant.product_id.supplier_ca_ma * \
                        quant.product_id.supplier_un_ca:
                    volume = quant.product_id.supplier_ma_width * \
                        quant.product_id.supplier_ma_height * \
                        quant.product_id.supplier_ma_length
                elif quant.package_id.pack_type == "box" and quant.qty == \
                        quant.product_id.supplier_un_ca:
                    volume = quant.product_id.supplier_ca_width * \
                        quant.product_id.supplier_ca_height * \
                        quant.product_id.supplier_ca_length
            if not volume:
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


# class product_putaway_strategy(osv.osv):
#     _inherit = 'product.putaway'

#     def _get_putaway_options(self, cr, uid, context=None):
#         res = super(product_putaway_strategy, self).\
#             _get_putaway_options(cr, uid, context=context)
#         res.extend([('product_pick_location', 'Product picking location')])
#         return res

#     columns = {
#         'method': fields.selection(_get_putaway_options, "Method",
#                                    required=True),
#     }

#     def putaway_apply(self, cr, uid, putaway_strat, product, context=None):
#         if putaway_strat.method == 'product_pick_location':
#             return product.picking_location_id.id
#         else:
#             return super(product_putaway_strategy, self).\
#                 putaway_apply(cr, uid, putaway_strat, product, context=context)


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
