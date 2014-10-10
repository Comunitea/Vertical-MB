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
        float("Filled Percentage", required=True,
              digits_compute=dp.get_precision('Product Price')),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',
                                        required=True),
    }
    _defaults = {
        'warehouse_id': lambda self, cr, uid, ctx=None:
        self.pool.get('stock.warehouse').search(cr, uid, [])[0],
    }

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
        pack_list = list(packs_set)
        res = sorted(pack_list, key=lambda p: p.volume, reverse=True)
        return res

    def _get_pack_candidates(self, cr, uid, quant_ids, lot_ids,
                             quant_ids_no_lot, context=None):
        """
        @param quant_ids: list of original quants
        @param lot_ids: fefo ordered list of lots
        @param quant_ids_no_lot: quants_without lot
        we need to search all packages related with lots and order them by
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

    def get_reposition_picking(self, cr, uid, ids, dest_id, prod, pack_cands,
                               context=None):
        """
        Get a reposition picking for ubication dest_id if its possible.
        We check pack_cands and try to replenish the maximum possible.
        @param dest_id: Ubication to replenish
        @param pack_cands: List of lists of packages ordered by volume dec
                           each list is a lot o packages without lotç
        @param return: Id of created picking or False
        """
        if context is None:
            context = {}
        pick_id = False
        loc_obj = self.pool.get('stock.location')
        t_pick = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        t_pack_op = self.pool.get("stock.pack.operation")

        obj = self.browse(cr, uid, ids[0], context=context)
        reposition_task_type_id = obj.warehouse_id.reposition_type_id.id
        storage_loc_id = obj.warehouse_id.storage_loc_id.id
        picking_loc_id = obj.warehouse_id.picking_loc_id.id

        loc = loc_obj.browse(cr, uid, dest_id, context=context)
        vol_aval = loc.available_volume
        idx = 0
        limit = len(pack_cands) - 1
        operation_dics = []
        packs_to_split = []
        total_move_qty = 0
        to_replenish_packs = []
        while vol_aval and idx <= limit:
            candidates = pack_cands[idx]  # list of packages ordered by volume
            for pack_obj in candidates:
                if pack_obj.volume <= vol_aval:
                    vol_aval -= pack_obj.volume
                    to_replenish_packs.append(pack_obj)
                elif pack_obj.pack_type == 'palet':
                    packs_to_split.append(pack_obj)
                    vol_aval = 0
            idx += 1

        if to_replenish_packs:
            for pack in to_replenish_packs:
                total_move_qty += pack.packed_qty
                op_vals = {
                    'picking_id': False,  # to set later, when pick created
                    'product_id': False,
                    'product_uom_id': False,
                    'product_qty': 1,
                    'package_id': pack.id,
                    'location_dest_id': dest_id,
                    'result_package_id': False,
                }
                operation_dics.append(op_vals)

        if packs_to_split:
            packs_to_split = sorted(packs_to_split, key=lambda p: p.volume)
            vol_mant = prod.supplier_pa_width * prod.supplier_pa_length * \
                prod.supplier_ma_height
            mant_units = prod.supplier.un_ca * prod.supplier.ca_ma
            num_mantles = vol_mant and math.floor(vol_aval / vol_mant) or False
            if num_mantles:
                total_move_qty += num_mantles * mant_units
                pack_obj = packs_to_split[0]
                op_vals = {
                    'picking_id': False,  # to set later, when pick created
                    'product_id': False,
                    'product_uom_id': False,
                    'product_qty': 1,
                    'package_id': pack.id,
                    'location_dest_id': dest_id,
                    'result_package_id': False,
                }
                operation_dics.append(op_vals)

        if total_move_qty > 0 and operation_dics:
            vals = {
                'state': 'draft',
                'name': '/',
                'picking_type_id': reposition_task_type_id
            }
            pick_id = t_pick.create(cr, uid, vals, context=context)
            vals = {
                'product_id': prod.id,
                'product_uom_qty': total_move_qty,
                'location_id': picking_loc_id,
                'location_dest_id': storage_loc_id,
                'product_uom': prod.uom_id.id,
                'picking_id': pick_id,
                # 'picking_type_id': pick_type.id,
                'warehouse_id': obj.warehouse_id.id,
                # 'name': _("Reposition")
            }
            move_obj.create(cr, uid, vals, context=context)
            t_pick.action_confirm(cr, uid, [pick_id], context=context)
            t_pick.action_assign(cr, uid, [pick_id], context=context)
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
        pick_ids = []
        obj = self.browse(cr, uid, ids[0], context=context)
        prod_ids = prod_obj.search(cr, uid, [('picking_location_id', '=',
                                              dest_id)], context=context,
                                   limit=1)
        if prod_ids:
            storage_id = obj.warehouse_id.storage_loc_id.id
            product = prod_obj.browse(cr, uid, prod_ids, context=context)[0]
            t_quant = self.pool.get('stock.quant')
            domain = [
                ('location_id', 'child_of', [storage_id]),
                ('package_id.pack_type', 'in', ['palet', 'box']),
                ('product_id', '=', product.id),
                ('qty', '>', 0),
            ]
            orderby = 'removal_date, in_date, id'  # aplly fefo
            quant_ids = t_quant.search(cr, uid, domain, order=orderby,
                                       context=context)

            import ipdb; ipdb.set_trace()
            lot_ids = []  # order fefo LOT IDS
            quant_ids_no_lot = []  # order fefo QUANTS IDS without lot

            # Get lots_ids orderd by fefo and quants_ids without lot
            for quant in t_quant.browse(cr, uid, quant_ids, context=context):
                if quant.lot_id and quant.lot_id.id not in lot_ids:
                    lot_ids.append(quant.lot_id.id)
                elif not quant.lot_id:
                    quant_ids_no_lot.append(quant.id)

            # Get list of lists of packages for each quant with or without lot
            pack_cands = self._get_pack_candidates(cr, uid, quant_ids, lot_ids,
                                                   quant_ids_no_lot,
                                                   context=context)
            if pack_cands:
                pick_ids = self.get_reposition_pickings(cr, uid, ids, dest_id,
                                                        product, pack_cands,
                                                        context=context)
        return pick_ids

    def get_reposition_list(self, cr, uid, ids, context=None):
        """
        For each picking location which percentege is under the specified in
        the wizard create a internal picking with reposition moves.
        """
        if context is None:
            context = {}
        loc_t = self.pool.get('stock.location')
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        pick_loc_id = wzd_obj.warehouse_id.picking_loc_id.id

        domain = [('location_id', 'child_of', [pick_loc_id])]
        # Get all picking locations
        picking_loc_ids = loc_t.search(cr, uid, domain, context=context)
        if not picking_loc_ids:
            raise osv.except_osv(_('Error!'),
                                 _('Picking locations does not exist'))

        # Obtener ubicaciones con un porcentaje de capacidad de ocupación
        # menores que el dado por el asistente
        selected_ids = []
        created_picks = []
        # get list of locations under wizard capacity filled
        for loc in loc_t.browse(cr, uid, picking_loc_ids, context):
            volume = loc.volume
            if volume:
                available = loc.available_volume
                filled = volume - available
                fill_per = (filled / volume) * 100.0
                if (fill_per <= wzd_obj.capacity):
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
        #A pick for each location, if nor operations delete the pick.
        for loc_id in selected_ids:
            if loc_id == 20:
                import ipdb; ipdb.set_trace()
            pick_id = self._get_reposition_operations(cr, uid, ids, loc_id,
                                                      context=context)
            if pick_id:
                created_picks.append(pick_id)
        if not created_picks:
            raise osv.except_osv(_('Error!'),
                                 _('Nothing to do.'))
        return True
