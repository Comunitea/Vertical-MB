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
#############################################################################
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import math


class reposition_wizard(osv.TransientModel):
    _name = "reposition.wizard"
    _rec_name = "warehouse_id"
    _columns = {
        'capacity': fields.
        float("Filled Percentage",
              digits_compute=dp.get_precision('Product Price'),
              help="Picking location with less or equal filled percentaje \
              will be proposed to reposition if is possible."),
        'limit': fields.float("Maximum Filled Percentage", required=True,
                              digits_compute=dp.get_precision
                              ('Product Price'),
                              help="When is reached stop the reposition"),

        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',
                                        required=True),
        'specific_locations': fields.boolean('Replenish specific locations'),
        'selected_loc_ids': fields.many2many('stock.location',
                                             'wzd_locs_rel',
                                             'wzd_id',
                                             'location_id',
                                             'Specific locations',
                                             help="Locations to replenish"),
        'product_ids': fields.many2one('product.product', 'Products')
    }
    _defaults = {
        'warehouse_id': lambda self, cr, uid, ctx=None:
        self.pool.get('stock.warehouse').search(cr, uid, [])[0],
        'limit': 100,
    }

    def onchange_loc_ids(self, cr, uid, ids, selected_loc_ids=False,
                         context=None):
        if not selected_loc_ids:
            return True
        selected_loc_ids = selected_loc_ids[0][2]
        product_ids = self.pool.get('product.product').search(
            cr, uid, [('picking_location_id', 'in', selected_loc_ids)],
            context=context)
        return {'domain': {'product_ids': [('id', 'in', product_ids)]}}

    def _get_volume_in_loc_by_prod(self, cr, uid, loc, prod_id,
                                   portion_product, context={}):
        # eliminar y usar get_available_volume_for_product de stock location
        quant_obj = self.pool.get('stock.quant')
        ope_obj = self.pool.get('stock.pack.operation')
        volume = 0.0
        quant_ids = quant_obj.search(cr, uid, [('location_id', 'child_of',
                                                loc.id),
                                               ('product_id', '=', prod_id)],
                                     context=context)
        volume = self.pool.get('stock.location')._get_quants_volume(
            cr, uid, quant_ids, context=context)
        domain = [
            ('location_dest_id', 'child_of', loc.id),
            ('processed', '=', 'false'),
            ('product_id', '=', prod_id),
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

    def _get_packs_ordered(self, cr, uid, quant_ids, context=None):
        """
        Get all different packages of quants, and order them by volume
        @param quant_ids: List of quants. We need it to get packages related
        @param return: A list of different packages of quants ordered by volume
        """
        if context is None:
            context = {}
        t_quant = self.pool.get("stock.quant")
        res = []
        packs_set = set()
        for quant in t_quant.browse(cr, uid, quant_ids, context=context):
            if quant.package_id:
                packs_set.add(quant.package_id)
            # TODO que pasa si no tiene paquete, estamos ignorando unid sueltas
        pack_list = list(packs_set)
        res = sorted(pack_list, key=lambda p: p.volume, reverse=True)
        return res

    def _get_pack_candidates(self, cr, uid, quant_ids, lot_ids,
                             quant_ids_no_lot, context=None):
        """
        @param quant_ids: list of original quants
        @param lot_ids: fefo ordered list of lots
        @param quant_ids_no_lot: quants_without lot
        We need to search all packages related with lots and order them by
        volume. Then we need to do the same with related pack of param
        quant_ids_no_lot
        @param return: List containing a list of packages ordered by volume
        for each lot, and a last list of packages ordered by volume without lot
        """
        if context is None:
            context = {}
        res = []
        t_quant = self.pool.get("stock.quant")
        # Get a list for each lot of packages ordered by fefo
        for lot_id in lot_ids:
            domain = [
                ('id', 'in', quant_ids),
                ('lot_id', '=', lot_id)
            ]

            quant_ids_with_lot = t_quant.search(cr, uid, domain,
                                                context=context)
            if quant_ids_with_lot:
                packs_ordered = self._get_packs_ordered(cr, uid,
                                                        quant_ids_with_lot,
                                                        context=context)
                if packs_ordered:
                    res.append(packs_ordered)
        # Get a list for each lot of packages ordered by fefo
        if quant_ids_no_lot:
            packs_ordered = self._get_packs_ordered(cr, uid, quant_ids_no_lot,
                                                    context=context)
            if packs_ordered:
                    res.append(packs_ordered)
        return res

    def _get_reposition_picking(self, cr, uid, ids, dest_id, prod,
                                portion_in_loc, pack_cands,
                                context=None):
        """
        Get a reposition picking for ubication dest_id if its possible.
        We check pack_cands and try to replenish the maximum possible.
        @param dest_id: Ubication to replenish
        @param pack_cands: List of lists of packages ordered by volume dec
                           each list is a lot or packages without lot
        @param return: Id of created picking or False
        """
        if context is None:
            context = {}
        pick_id = False
        loc_obj = self.pool.get('stock.location')
        t_pick = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        t_pack_op = self.pool.get("stock.pack.operation")
        t_pack = self.pool.get("stock.quant.package")

        obj = self.browse(cr, uid, ids[0], context=context)
        pick_loc_obj = prod.picking_location_id
        reposition_task_type_id = obj.warehouse_id.reposition_type_id.id
        storage_loc_id = pick_loc_obj.get_general_zone('storage')
        picking_loc_id = pick_loc_obj.get_general_zone('picking')

        loc = loc_obj.browse(cr, uid, dest_id, context=context)
        product_vol = loc.volume / portion_in_loc
        vol_aval, filled_per = self._get_volume_in_loc_by_prod(
            cr, uid, loc, prod.id, portion_in_loc, context)
        idx = 0
        limit = len(pack_cands) - 1
        operation_dics = []
        packs_to_split = []
        total_move_qty = 0
        to_replenish_packs = []
        while vol_aval and filled_per < obj.limit and idx <= limit:
            candidates = pack_cands[idx]  # list of packages ordered by volume
            for pack_obj in candidates:
                quants_by_prod = pack_obj.get_products_quants()
                multipack = True if len(quants_by_prod) > 1 else False
                if pack_obj.volume <= vol_aval and not multipack:
                    vol_aval -= pack_obj.volume
                    vol_fill = loc.volume - vol_aval
                    filled_per = loc.volume and (vol_fill / loc.volume) or 0.0
                    to_replenish_packs.append(pack_obj)
                else:
                    packs_to_split.append(pack_obj)
                    idx = limit + 1  # force out of while
            idx += 1

        force_quants_assign = []  # to reserve the quants of the operations
        if to_replenish_packs:
            for pack in to_replenish_packs:
                total_move_qty += pack.packed_qty
                op_vals = {
                    'picking_id': False,  # to set later, when pick created
                    'product_id': False,
                    'product_uom_id': False,
                    'product_qty': 1,
                    'package_id': pack.id,
                    'location_id': pack.location_id.id,
                    'location_dest_id': dest_id,
                    'result_package_id': False,
                    'lot_id': pack.packed_lot_id and
                    pack.packed_lot_id.id or False,
                    'uos_id': pack.uos_id.id,
                    'uos_qty': pack.uos_qty}
                for q in pack.quant_ids:
                    force_quants_assign.append((q, q.qty))
                operation_dics.append(op_vals)

        if packs_to_split:
            # split the pack with lowest volume, split multiproduct palets
            packs_to_split = sorted(packs_to_split, key=lambda p: p.volume)
            vol_mant = prod.pa_width * prod.pa_length * \
                prod.ma_height
            mant_units = prod.get_num_mantles(1, total_uom_mantles=True)
            num_mantles = vol_mant and math.floor(vol_aval / vol_mant) or 0.0
            max_units = num_mantles * mant_units
            if num_mantles:
                total_move_qty += max_units
                pack_obj = packs_to_split[0]  # the little pack
                qtys_by_prod = pack_obj.get_products_qtys()
                packed_qty = qtys_by_prod[prod]
                pack_qty = packed_qty if max_units > packed_qty else max_units
                new_pack_id = t_pack.create(cr, uid, {})
                uos_qty = prod.uom_qty_to_uos_qty(pack_qty, pack_obj.uos_id.id)
                op_vals = {
                    'picking_id': False,  # to set later, when pick created
                    'product_id': prod.id,
                    'product_uom_id': prod.uom_id.id,
                    'product_qty': pack_qty,
                    'package_id': pack_obj.id,
                    'location_id': pack_obj.location_id.id,
                    'location_dest_id': dest_id,
                    'result_package_id': new_pack_id,
                    'lot_id': pack_obj.packed_lot_id and
                    pack_obj.packed_lot_id.id or False,
                    'uos_id': pack_obj.uos_id.id,
                    'uos_qty': uos_qty}
                assigned = 0
                rest_pack_qty = pack_qty
                for q in pack_obj.quant_ids:
                    if q.product_id.id == prod.id and assigned < rest_pack_qty:
                        if rest_pack_qty > q.qty:
                            force_quants_assign.append((q, q.qty))
                            assigned += q.qty
                            rest_pack_qty -= assigned
                        else:
                            force_quants_assign.append((q, rest_pack_qty))
                            assigned += rest_pack_qty
                            rest_pack_qty -= assigned
                operation_dics.append(op_vals)

        camera_id = loc.get_camera()
        if not camera_id:
            raise osv.except_osv(_('Error!'),
                                 _('The location to replenish %s is not child\
                                    of a camera location, you must configure\
                                    it well' % loc.name))
        if total_move_qty > 0 and operation_dics:
            vals = {
                'state': 'draft',
                'name': '/',
                'picking_type_id': reposition_task_type_id,
                'task_type': 'reposition',
                'camera_id': camera_id,  # To search picking for camera
            }
            pick_id = t_pick.create(cr, uid, vals, context=context)
            vals = {
                'product_id': prod.id,
                'product_uom_qty': total_move_qty,
                'location_id': storage_loc_id,
                'location_dest_id': picking_loc_id,
                'product_uom': prod.uom_id.id,
                'picking_id': pick_id,
                'warehouse_id': obj.warehouse_id.id,
                'name': _("Reposition")
            }
            move_obj.create(cr, uid, vals, context=context)
            t_pick.action_confirm(cr, uid, [pick_id], context=context)
            ctx = context.copy()  # force the assignement
            ctx.update({'force_quants_location': force_quants_assign})
            t_pick.action_assign(cr, uid, [pick_id], context=ctx)
            t_pick.do_prepare_partial(cr, uid, [pick_id], context=context)
            pick_obj = t_pick.browse(cr, uid, pick_id, context=context)
            for op in pick_obj.pack_operation_ids:
                op.unlink()
            for vals in operation_dics:
                vals['picking_id'] = pick_id
                t_pack_op.create(cr, uid, vals, context=context)
        return pick_id

    def _get_reposition_operations(self, cr, uid, ids, dest_id, context=None):
        """
        Create operations in the reposition picking.(pick_id)
        dest_id is the picking location to replace. This method gets
        several pack operations to replace products from a storage location
        to dest_id
        """
        if context is None:
            context = {}
        prod_obj = self.pool.get('product.product')
        pick_id = False
        prod_ids = prod_obj.search(cr, uid, [('picking_location_id', '=',
                                              dest_id)], context=context)
        prod_in_loc = len(prod_ids)
        wzd = self.browse(cr, uid, ids[0], context)
        if wzd.product_ids:
            prod_ids = [x for x in prod_ids if x in wzd.product_ids._ids]
        for prod_id in prod_ids:
            product = prod_obj.browse(cr, uid, prod_id, context=context)[0]
            pick_loc_obj = product.picking_location_id
            storage_id = pick_loc_obj.get_general_zone('storage')
            t_quant = self.pool.get('stock.quant')
            domain = [
                ('location_id', 'child_of', [storage_id]),
                ('product_id', '=', product.id),
                ('qty', '>', 0),
            ]
            orderby = 'removal_date, in_date, id'  # aplly fefo
            quant_ids = t_quant.search(cr, uid, domain, order=orderby,
                                       context=context)

            lot_ids = []  # order fefo LOT IDS
            quant_ids_no_lot = []  # order fefo QUANTS IDS without lot

            # Get lots_ids orderd by fefo and quants_ids without lot
            for quant in t_quant.browse(cr, uid, quant_ids, context=context):
                if quant.lot_id and quant.lot_id.id not in lot_ids:
                    lot_ids.append(quant.lot_id.id)
                elif not quant.lot_id:
                    quant_ids_no_lot.append(quant.id)
                    quant_ids.remove(quant.id)

            # Get list of lists of packages for each quant with or without lot
            pack_cands = self._get_pack_candidates(cr, uid, quant_ids, lot_ids,
                                                   quant_ids_no_lot,
                                                   context=context)
            if pack_cands:
                pick_id = self._get_reposition_picking(cr, uid, ids, dest_id,
                                                       product, prod_in_loc,
                                                       pack_cands,
                                                       context=context)
        return pick_id

    def get_reposition_list(self, cr, uid, ids, context=None):
        """
        For each picking location which percentege is under the specified in
        the wizard create a internal picking with reposition moves.
        """
        if context is None:
            context = {}
        loc_t = self.pool.get('stock.location')
        wzd_obj = self.browse(cr, uid, ids[0], context=context)

        domain = [('zone', '=', 'picking')]
        # Get all picking locations
        picking_loc_ids = loc_t.search(cr, uid, domain, context=context)
        if not picking_loc_ids:
            raise osv.except_osv(_('Error!'),
                                 _('Picking locations does not exist'))

        # Obtener ubicaciones con un porcentaje de capacidad de ocupación
        # menores que el dado por el asistente
        selected_ids = []
        created_picks = []
        if wzd_obj.selected_loc_ids:
            selected_ids = [x.id for x in wzd_obj.selected_loc_ids]
        else:
            # get list of locations under wizard capacity filled
            for loc in loc_t.browse(cr, uid, picking_loc_ids, context):
                volume = loc.volume
                if volume:
                    available = loc.available_volume
                    filled = volume - available
                    fill_per = (filled / volume) * 100.0
                    if fill_per <= wzd_obj.capacity:
                        selected_ids.append(loc.id)
        if not selected_ids:
            raise osv.except_osv(_('Error!'),
                                 _('No picking location matching with \
                                    specified capacity.'))

        # create a pick of reposition_task_type with pack operations to
        # replenih productos from specific storage location to picking zone
        if not wzd_obj.warehouse_id.reposition_type_id:
            raise osv.except_osv(_('Error!'), _('No reposition type founded\
                                                 You must define the picking\
                                                 type in the warehouse.'))
        # A pick for each location, if not operations delete the pick.
        for loc_id in selected_ids:
            pick_id = self._get_reposition_operations(cr, uid, ids, loc_id,
                                                      context=context)
            if pick_id:
                created_picks.append(pick_id)
        if not created_picks:
            raise osv.except_osv(_('Error!'),
                                 _('Nothing to do.'))

        # Display the created pickings
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = \
            tuple(mod_obj.get_object_reference(cr, uid, 'stock',
                                               'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid,
                                                             action_id,
                                                             context=context)
        action['context'] = {}  # override the context to avoid default filters
        if len(created_picks) > 1:
            action['domain'] = "[('id', 'in',\
                               [" + ','.join(map(str, created_picks)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock',
                                               'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = created_picks[0]
        return action
