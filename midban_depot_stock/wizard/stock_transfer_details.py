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


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    midban_operations = fields.Boolean(string='Custom midban operations',
                                       related='picking_id.midban_operations',
                                       readonly=True)

    picking_type_code = fields.Char('Picking code',
                                    related='picking_id.picking_type_code')

    # def _get_pack_type_operation(self, item, pack_type, num):
    #     """
    #     Return a dictionary containing the values to create a pack operation
    #     with pack and his pack type setted when we can, or a operation without
    #     package in other case.
    #     MANTLES WILL BE GROUPED INTO PALETES
    #     """
    #     res = []
    #     t_pack = self.env['stock.quant.package']
    #     op_vals = {
    #         'location_id': item.sourceloc_id.id,
    #         'product_id': item.product_id.id,
    #         'product_uom_id': item.product_uom_id.id,
    #         'location_dest_id': item.destinationloc_id.id,
    #         'picking_id': item.transfer_id.picking_id.id,
    #         'lot_id': item.lot_id.id
    #     }
    #     ma_pa = item.product_id.supplier_ma_pa
    #     ca_ma = item.product_id.supplier_ca_ma
    #     un_ca = item.product_id.supplier_un_ca

    #     if pack_type not in ['palet', 'mantle', 'box']:  # Only Units
    #         op_vals.update({
    #             'product_qty': num,
    #         })
    #         res.append(op_vals)

    #     elif pack_type == 'mantle':  # Group in a same palet the mantles.
    #         pack_obj = t_pack.create({'pack_type': 'palet'})
    #         new_name = pack_obj.name.replace("PACK", 'PALET')
    #         pack_obj.write({'name': new_name})
    #         pack_units = ca_ma * un_ca
    #         op_vals.update({
    #             'result_package_id': pack_obj.id,
    #             'product_qty': pack_units * num
    #         })
    #         res.append(dict(op_vals))
    #     else:  # create a different pack and operation if box or palet
    #         for n in range(num):
    #             if pack_type == 'palet':
    #                 pack_units = ma_pa * ca_ma * un_ca
    #                 pack_name = 'PALET'
    #             elif pack_type == 'box':
    #                 pack_units = un_ca
    #                 pack_name = 'CAJA'
    #             pack_obj = t_pack.create({'pack_type': pack_type})
    #             new_name = pack_obj.name.replace("PACK", pack_name)
    #             pack_obj.write({'name': new_name})
    #             op_vals.update({
    #                 'result_package_id': pack_obj.id,
    #                 'product_qty': pack_units,
    #             })
    #             res.append(dict(op_vals))
    #     return res

    # def _get_unit_conversions(self, item):
    #     """
    #     Get the expected partition in palets, mantles and units ussing the
    #     measures of product sheet in suppliers page. (supplier measures).
    #     It say to us how the products are recived from the supplier
    #     """
    #     res = [0, 0, 0, 0]
    #     prod_obj = item.product_id
    #     item_qty = item.quantity

    #     un_ca = prod_obj.supplier_un_ca
    #     ca_ma = prod_obj.supplier_ca_ma
    #     ma_pa = prod_obj.supplier_ma_pa

    #     box_units = un_ca
    #     mantle_units = un_ca * ca_ma
    #     palet_units = un_ca * ca_ma * ma_pa

    #     remaining_qty = item_qty
    #     int_pal = 0
    #     int_man = 0
    #     int_box = 0
    #     int_units = 0

    #     while remaining_qty > 0:
    #         if remaining_qty >= palet_units:
    #             remaining_qty -= palet_units
    #             int_pal += 1
    #         elif remaining_qty >= mantle_units:
    #             remaining_qty -= mantle_units
    #             int_man += 1
    #         elif remaining_qty >= box_units:
    #             remaining_qty -= box_units
    #             int_box += 1
    #         else:
    #             int_units = remaining_qty
    #             remaining_qty = 0
    #     res = [int_pal, int_man, int_box, int_units]
    #     return res

    # def _propose_pack_operations_old(self, item):
    #     res = []
    #     int_pal, int_man, int_box, units = self._get_unit_conversions(item)

    #     if int_pal:
    #         pa_dics = self._get_pack_type_operation(item, 'palet', int_pal)
    #         res.extend(pa_dics)
    #     if int_man:
    #         ma_dics = self._get_pack_type_operation(item, 'mantle', int_man)
    #         res.extend(ma_dics)
    #     if int_box:
    #         bo_dics = self._get_pack_type_operation(item, 'box', int_box)
    #         res.extend(bo_dics)
    #     if units:
    #         un_dic = self._get_pack_type_operation(item, 'units', units)
    #         res.extend(un_dic)
    #     return res
# #############################################################################
# #############################################################################

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
            ('qty', '>', 0),
            ('location_id', 'in', storage_loc_ids),
        ]
        quant_objs = t_quant.search(domain)
        if quant_objs:
            res = True
        return res

    def _is_picking_loc_available(self, product, prop_qty, pack):
        """
        Return True whe picking is available and no older reference in storage
        """
        res = False
        if not product.picking_location_id:
            raise except_orm(_('Error!'), _('Not picking location.'))

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
        new_index = index == len(sorted_locs) - 1 and index - 1 or index + 1
        return sorted_locs[new_index].id

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

    def _get_loc_and_qty(self, r_qty, product):
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
            raise except_orm(_('Error!'), _('Not picking location.'))
        pick_loc = product.picking_location_id
        loc_id = False
        prop_qty, pack = self.get_max_qty_to_process(r_qty, product)
        stop = False
        while prop_qty and not stop:
            # Try to put in picking location
            domain = []
            if pack == 'unit' or \
                    self._is_picking_loc_available(product, prop_qty, pack):
                loc_id = pick_loc.id  # Return picking loc id
                stop = True
            elif pack == 'palet':
                vol_palet = self._get_volume_for(pack, prop_qty, product)
                domain = [('available_volume', '>', vol_palet),
                          ('storage_type', '=', 'standard')]
                storage_loc_ids = \
                    pick_loc.get_locations_by_zone('storage',
                                                   add_domain=domain)
                if storage_loc_ids:
                    loc_id = \
                        self._search_closest_pick_location(product,
                                                           storage_loc_ids)
                    stop = True
                else:
                    mantle_units = product.un_ca * product.ca_ma
                    if prop_qty <= mantle_units:  # Only 1 mantle!! exit
                        stop = True
                    else:
                        prop_qty -= mantle_units  # Remove 1 mantle
            elif pack == 'box':
                vol_box = self._get_volume_for(pack, prop_qty, product)
                domain = [('available_volume', '>', vol_box),
                          ('storage_type', '=', 'boxes')]
                storage_loc_ids = \
                    pick_loc.get_locations_by_zone('storage',
                                                   add_domain=domain)
                if storage_loc_ids:
                    loc_id = \
                        self._search_closest_pick_location(product,
                                                           storage_loc_ids)
                stop = True
        return [loc_id, prop_qty, pack]

    def _create_pack_operation(self, item, loc_id, located_qty, pack):
        t_pack = self.env['stock.quant.package']
        t_ope = self.env['stock.pack.operation']
        op_vals = {
            'location_id': item.sourceloc_id.id,
            'product_id': item.product_id.id,
            'product_qty': located_qty,
            'product_uom_id': item.product_uom_id.id,
            'location_dest_id': item.destinationloc_id.id,
            'chained_loc_id': loc_id,
            'picking_id': item.transfer_id.picking_id.id,
            'lot_id': item.lot_id.id,
            'result_package_id': False
        }
        if pack in ['palet', 'box']:
            pack_obj = t_pack.create({'pack_type': pack})
            pack_name = pack == 'palet' and 'PALET' or 'CAJA'
            new_name = pack_obj.name.replace("PACK", pack_name)
            op_vals['result_package_id'] = pack_obj.id
            pack_obj.write({'name': new_name})
        t_ope.create(op_vals)
        return True

    def _propose_pack_operations(self, item):
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
            loc_id, located_qty, pack = self._get_loc_and_qty(remaining_qty,
                                                              product)
            if loc_id and located_qty:
                self._create_pack_operation(item, loc_id, located_qty, pack)
                remaining_qty -= located_qty
            else:
                remaining_qty = -1
        return remaining_qty == 0.0 and True or False

    @api.one
    def prepare_package_type_operations(self):
        for op in self.picking_id.pack_operation_ids:
            op.unlink()
        for item in self.item_ids:
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
