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
# import math


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
        dest_id is the picking location to replace. This method gets
        several pack operations to replace products from a storage location
        to dest_id
        """
        if context is None:
            context = {}
        prod_obj = self.pool.get('product.product')
        loc_obj = self.pool.get('stock.location')

        created_moves = []
        obj = self.browse(cr, uid, ids[0], context=context)
        # pick_type = obj.warehouse_id.reposition_type_id
        # move_obj = self.pool.get('stock.move')
        prod_ids = prod_obj.search(cr, uid, [('picking_location_id', '=',
                                              dest_id)], context=context,
                                   limit=1)
        loc = loc_obj.browse(cr, uid, dest_id, context=context)
        if prod_ids:
            storage_id = obj.warehouse_id.storage_loc_id.id
            product = prod_obj.browse(cr, uid, prod_ids, context=context)[0]

            # vol_aval = loc.available_volume
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

        return created_moves

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
        reposition_task_type_id = wzd_obj.warehouse_id.reposition_type_id.id
        vals = {'state': 'draft',
                'name': '/',
                'picking_type_id': reposition_task_type_id}
        pick_id = t_pick.create(cr, uid, vals, context=context)

        #A pick for each location, if nor operations delete the pick.
        for loc_id in selected_ids:
            if loc_id == 20:
                import ipdb; ipdb.set_trace()
            vals = {'state': 'draft',
                    'name': '/',
                    'picking_type_id': reposition_task_type_id}
            pick_id = t_pick.create(cr, uid, vals, context=context)
            created_moves = self._get_reposition_operations(cr, uid, ids,
                                                            loc_id,
                                                            pick_id,
                                                            context=context)
            if created_moves:
                t_pick.action_confirm(cr, uid, [pick_id], context=context)
                t_pick.action_assign(cr, uid, [pick_id], context=context)
                t_pick.do_prepare_partial(cr, uid, [pick_id], context=context)
                created_picks.append(pick_id)

            else:
                t_pick.unlink(cr, uid, [pick_id], context=context)

        if not created_picks:
            raise osv.except_osv(_('Error!'),
                                 _('Nothing to do.'))

        return
