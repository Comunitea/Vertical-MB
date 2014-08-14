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

    def _get_reposition_operations(self, cr, uid, ids, dest_id, pick_id,
                                   context=None):
        """
        Create operations in the reposition picking.(pick_id)
        dest_id is the picking location to replace. This method several pack
        operations to replace products from a storage location to dest_id
        """
        if context is None:
            context = {}
        newm = False
        obj = self.browse(cr, uid, ids[0], context=context)
        pick_type = obj.warehouse_id.reposition_type_id
        move_obj = self.pool.get('stock.move')
        prod_obj = self.pool.get('product.product')
        prod_ids = prod_obj.search(cr, uid, [('picking_location_id', '=',
                                              dest_id)], context=context,
                                   limit=1)
        if prod_ids:
            context['compute_child'] = True
            context['location'] = obj.warehouse_id.storage_loc_id.id
            product = prod_obj.browse(cr, uid, prod_ids, context=context)[0]
            unit_volume = product.supplier_un_width * \
                product.supplier_un_height * product.supplier_un_length

            requested_units = obj.capacity / unit_volume
            if product.virtual_available >= requested_units:
                newm = move_obj.create(cr, uid,
                                       {'product_id': product.id,
                                        'product_uom_qty': requested_units,
                                        'location_id': pick_type.
                                        default_location_src_id.id,
                                        'location_dest_id': pick_type.
                                        default_location_dest_id.id,
                                        'product_uom': product.uom_id.id,
                                        'picking_id': pick_id,
                                        'picking_type_id': pick_type.id,
                                        'warehouse_id': obj.warehouse_id.id},
                                       context=context)

        return newm

    def get_reposition_list(self, cr, uid, ids, context=None):
        """
        For each picking location which percentege is under the specified in
        the wizard create a internal picking with reposition moves.
        """
        if context is None:
            context = {}
        loc_t = self.pool.get('stock.location')
        t_pick = self.pool.get("stock.picking")
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
        reposition_task_type_id = wzd_obj.warehouse_id.reposition_type_id.id
        vals = {'state': 'draft',
                'name': '/',
                'picking_type_id': reposition_task_type_id}
        pick_id = t_pick.create(cr, uid, vals, context=context)
        created_moves = []
        for loc_id in selected_ids:
            newm = self._get_reposition_operations(cr, uid, ids, loc_id,
                                                   pick_id, context=context)
            if newm:
                created_moves.append(newm)
        if created_moves:
            t_pick.action_confirm(cr, uid, [pick_id], context=context)
            t_pick.action_assign(cr, uid, [pick_id], context=context)
            t_pick.prepare_package_type_operations(cr, uid, [pick_id],
                                                   context=context)
        else:
            raise osv.except_osv(_('Error!'),
                                 _('Nothing to do.'))

        return
