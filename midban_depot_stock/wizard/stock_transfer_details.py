# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from datetime import datetime
import math


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    midban_operations = fields.Boolean(string='Custom midban operations',
                                       related='picking_id.midban_operations',
                                       readonly=True)

    picking_type_code = fields.Char('Picking code',
                                    related='picking_id.picking_type_code')

    def _get_volume_for(self, pack, prop_qty, product, picking_zone=False):
        volume = 0.0
        un_ca = product.un_ca
        ca_ma = product.ca_ma
        mantle_units = un_ca * ca_ma
        if pack == 'palet':
            num_mant = prop_qty // mantle_units
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

    def _older_refernce_in_storage(self, product):
        """
        Search for quants of param product in his storage locations
        """
        res = False
        t_quant = self.env['stock.quant']
        pick_loc = product.picking_location_id
        storage_loc_ids = pick_loc.get_locations_by_zone('storage')
        domain = [
            # ('company_id', '=', wh_obj.company_id.id),
            ('product_id', '=', product.id),
            # ('qty', '>', 0),
            ('location_id', 'in', storage_loc_ids),
        ]
        quant_objs = t_quant.search(domain)
        net_qty = 0.0
        for quant in quant_objs:
            net_qty += quant.qty
        if quant_objs and net_qty:
            res = True
        return res

    def _is_picking_loc_available(self, product, prop_qty, pack):
        """
        Return True whe picking is available and no older reference in storage
        """
        res = False
        if not product.picking_location_id:
            raise except_orm(_('Error!'), _('Not picking location for product \
                             %s.' % product.name))

        pick_loc = product.picking_location_id
        volume = self._get_volume_for(pack, prop_qty, product,
                                      picking_zone=True)
        if not pick_loc.filled_percent:  # If empty add wood volume
            width_wood = product.pa_width
            length_wood = product.pa_length
            height_wood = product.palet_wood_height
            wood_volume = width_wood * length_wood * height_wood
            vol_aval = pick_loc.available_volume - wood_volume
        else:
            vol_aval = pick_loc.available_volume

        old_ref = self._older_refernce_in_storage(product)
        if (not old_ref and volume <= vol_aval):
            res = True
        return res

    def _search_closest_pick_location(self, prod_obj, free_loc_ids):
        loc_t = self.env['stock.location']
        if not free_loc_ids:
            raise except_orm(_('Error!'), _('No empty locations.'))
        free_loc_ids.append(prod_obj.picking_location_id.id)
        locs = loc_t.browse(free_loc_ids)
        sorted_locs = sorted(locs, key=lambda l: l.name)
        index = sorted_locs.index(prod_obj.picking_location_id)
        if index == (len(sorted_locs) - 1):
            new_index = index - 1
        else:
            new_index = index + 1
        free_loc_ids.remove(prod_obj.picking_location_id.id)
        return sorted_locs[new_index]

    def get_max_qty_to_process(self, r_qty, product):
        """
        Obtain the max qty to put in a pack, first palet units, else the
        maximun number of mantle units, else boxe units, else the r_qty units
        """
        un_ca = product.un_ca
        ca_ma = product.ca_ma
        ma_pa = product.ma_pa

        box_units = un_ca
        mantle_units = un_ca * ca_ma
        palet_units = un_ca * ca_ma * ma_pa
        prop_qty = r_qty  # Proposed qty to ubicate
        pack = 'units'
        if r_qty >= palet_units:
            prop_qty = palet_units
            pack = 'palet'
        elif r_qty >= mantle_units:
            num_mantles = 0
            num_mantles = r_qty // mantle_units  # Maximum entire mantles
            prop_qty = num_mantles * mantle_units
            pack = 'palet'
        elif r_qty >= box_units:
            prop_qty = box_units
            pack = 'box'
        return [prop_qty, pack]

    def _get_loc_and_qty(self, r_qty, product, multipack=False):
        """
        @parm r_qty: remaining_qty for the item considered
        @param product: product to locate
        @return list with the location and the qty located or [False, 0]
        First we consider the maximum logistic qty of units for the
        remainig_qty.
        We try to ubicate first in the picking location if available space
        and not older reference of product in storage. In other case:
        If remainig qty more than a palet we try to ubicate the palet.
        If not available space for palet were consider a qty of
        palet - 1 mantle
        We remove mantle units from the palet and try to find a location.
        If we have only a mantle and we can't find a location we return False
        to raise then an Error
        If remaining_qty is less than a mantle we try to ubicate boxes in boxes
        locationsa
        If remaining_qty if less than boxes we force the units to the picking
        location
        """
        if not product.picking_location_id:
            raise except_orm(_('Error!'), _('Not picking location. Maybe is a \
                                             cross dock order'))
        pick_loc = product.picking_location_id
        loc_obj = False
        prop_qty, pack = self.get_max_qty_to_process(r_qty, product)
        stop = False
        if multipack:
            if prop_qty < r_qty:
                stop = True
        while prop_qty and not stop:
            # Try to put in picking location
            # domain = []
            if pack == 'units' or \
                    self._is_picking_loc_available(product, prop_qty, pack):
                loc_obj = pick_loc  # Return picking loc id
                stop = True
            elif pack == 'palet' and not multipack:
                vol_palet = self._get_volume_for(pack, prop_qty, product)
                # domain = [('available_volume', '>', vol_palet),
                #           ('storage_type', '=', 'standard')]
                # storage_loc_ids = \
                #     pick_loc.get_locations_by_zone('storage',
                #                                    add_domain=domain)
                # Comentado por problemas de rendimiento con muchas ubicaciones
                storage_loc_ids = pick_loc.get_locations_by_zone('storage')
                if storage_loc_ids:
                    ctl = True
                    while ctl and storage_loc_ids:
                        loc_obj = \
                            self._search_closest_pick_location(product,
                                                               storage_loc_ids)
                        if loc_obj.available_volume > vol_palet:
                            ctl = False
                        else:
                            storage_loc_ids.remove(loc_obj.id)

                    stop = True
                else:
                    mantle_units = product.un_ca * product.ca_ma
                    if prop_qty <= mantle_units:  # Only 1 mantle!! exit
                        stop = True
                    else:
                        prop_qty -= mantle_units  # Remove 1 mantle
            elif pack == 'box' and not multipack:
                vol_box = self._get_volume_for(pack, prop_qty, product)
                # domain = [('available_volume', '>', vol_box),
                #           ('storage_type', '=', 'boxes')]
                # storage_loc_ids = \
                #     pick_loc.get_locations_by_zone('storage',
                #                                    add_domain=domain)
                # Comentado por problemas de rendimiento con muchas ubicaciones
                storage_loc_ids = pick_loc.get_locations_by_zone('storage')
                if storage_loc_ids:
                    ctl = True
                    while ctl and storage_loc_ids:
                        loc_obj = \
                            self._search_closest_pick_location(product,
                                                               storage_loc_ids)

                        if loc_obj.available_volume > vol_box:
                            ctl = False
                        else:
                            storage_loc_ids.remove(loc_obj.id)
                stop = True
            elif multipack:
                stop = True
        return [loc_obj and loc_obj.id or False, prop_qty, pack]

    def _create_pack_operation(self, item, loc_id, located_qty, pack,
                               multipack=False):
        t_pack = self.env['stock.quant.package']
        t_ope = self.env['stock.pack.operation']
        op_vals = {
            'location_id': item.sourceloc_id.id,
            'product_id': item.product_id.id,
            'product_qty': located_qty,
            'product_uom_id': item.product_uom_id.id,
            'location_dest_id': item.destinationloc_id.id,
            'chained_loc_id': loc_id,
            'picking_id': self.picking_id.id,
            'lot_id': item.lot_id.id,
            'result_package_id': False,
            'owner_id': item.owner_id.id,
            'date': item.date if item.date else datetime.now(),
        }
        # import ipdb; ipdb.set_trace()
        if pack in ['palet', 'box']:
            if multipack:
                multipack.name = 'M.' + multipack.name
                op_vals['result_package_id'] = multipack.id
            else:
                pack_obj = t_pack.create({'pack_type': pack})
                pack_name = pack == 'palet' and 'PALET' or 'CAJA'
                new_name = pack_obj.name.replace("PACK", pack_name)
                op_vals['result_package_id'] = pack_obj.id
                pack_obj.write({'name': new_name})
        t_ope.create(op_vals)
        return True

    def _propose_pack_operations(self, item, multipack=False):
        """
        This method try to get a maximum pack logisic unit and a location for
        it.
        If not space for maximum pack logistic unit we get another lower,
        removing mantle by mantle and trying to find available space.
        If not space for a mantle, location cant be founded and return False
        """
        remaining_qty = item.quantity
        product = item.product_id
        while remaining_qty > 0.0:
            loc_id, located_qty, pack = \
                self._get_loc_and_qty(remaining_qty, product,
                                      multipack=multipack)
            if loc_id and located_qty:
                self._create_pack_operation(item, loc_id, located_qty, pack)
                remaining_qty -= located_qty
            else:
                if multipack:
                    item.quantity = remaining_qty
                remaining_qty = -1
        return remaining_qty == 0.0 and True or False

    def _get_multipack_operations(self, item_lst):
        sum_heights = 0
        width_wood = 0
        length_wood = 0
        for item in item_lst:
            product = item.product_id
            if product.pa_width > width_wood:
                width_wood = product.pa_width
                length_wood = product.pa_length
            qty = item.quantity
            un_ca = product.un_ca
            ca_ma = product.ca_ma
            mantle_height = product.ma_height

            mantle_units = un_ca * ca_ma
            if qty < mantle_units:
                raise except_orm(_('Error'),
                                 _('You are trying to mount a multiproduct \
                                    palet, with product %s and %s units. \
                                    You need at least one mantle (%s \
                                     units)' % (product.name, qty,
                                                mantle_units)))
            # Maximum entire mantles
            num_mantles = math.ceil(qty / mantle_units)
            sum_heights += num_mantles * mantle_height

        vol_pack = width_wood * length_wood * sum_heights
        pick_loc = product.picking_location_id
        storage_loc_ids = pick_loc.get_locations_by_zone('storage')
        if not storage_loc_ids:
            raise except_orm(_('Error'), _('Not free space to alocate \
                                            multiproduct pack'))
        ctl = True
        while ctl and storage_loc_ids:
            loc_obj = self._search_closest_pick_location(product,
                                                         storage_loc_ids)
            if loc_obj.available_volume > vol_pack:
                ctl = False
            else:
                storage_loc_ids.remove(loc_obj.id)
        if not ctl:  # location founded
            for item in item_lst:
                self._create_pack_operation(item, loc_obj.id, item.quantity,
                                            'palet',
                                            multipack=item.result_package_id)
        return

    @api.one
    def prepare_package_type_operations(self):
        for op in self.picking_id.pack_operation_ids:
            op.unlink()
        import ipdb; ipdb.set_trace()
        items_to_propose = []
        # Separate items to propose of multipacks items
        for item in self.item_ids:
            if not item.result_package_id:
                self.item_ids -= item  # Quit item because will be proposed
                items_to_propose.append(item)

        # for items proposed to be part of a multiproduct pack, try to locate
        # it in picking location all possible.
        for item in self.item_ids:
            done = self._propose_pack_operations(item, multipack=True)
            if done:
                self.item_ids -= item  # Quit item because it is alocated

        # Group items with pack setted by pack
        items_by_pack = {}
        for item in self.item_ids:  # item_ids only with pack explicit setted
            if item.result_package_id not in items_by_pack:
                items_by_pack[item.result_package_id] = [item]
            else:
                items_by_pack[item.result_package_id].append(item)

        # Check if the finally multiproducts packs proposed have products of
        # same camera and create operations
        for pack in items_by_pack:
            camera_founded = False
            # Picking location to locate the multipack closest to it
            for item in items_by_pack[pack]:
                product = item.product_id
                prod_camera = product.picking_location_id.get_camera()
                if not camera_founded:
                    camera_founded = prod_camera
                elif camera_founded != prod_camera:
                    raise except_orm(_('Error!'),
                                     _('You are trying to mount a multiproduct\
                                        palet, with products of different \
                                        cameras'))
            self._get_multipack_operations(items_by_pack[pack])

        # Get operations for monoproduct packs
        for item in items_to_propose:
            sucess = self._propose_pack_operations(item)
            if sucess:
                self.picking_id.write({'midban_operations': True})
            else:
                raise except_orm(_('Error!'), _('Not enought free space.'))
        return True

    @api.one
    def do_detailed_transfer(self):
        res = super(stock_transfer_details, self).do_detailed_transfer()
        if self.picking_id.cross_dock and self.move_lines and \
                self.move_lines[0].move_dest_id:
            related_pick = self.move_lines[0].move_dest_id.picking_id
            related_pick.do_prepare_partial()
            related_pick.write({'midban_operations': True})
        return res
