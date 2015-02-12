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


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    midban_operations = fields.Boolean(string='Custom midban operations',
                                       related='picking_id.midban_operations',
                                       readonly=True)

    picking_type_code = fields.Char('Picking code',
                                    related='picking_id.picking_type_code')

    def _get_pack_type_operation(self, item, pack_type, num):
        """
        Return a dictionary containing the values to create a pack operation
        with pack and his pack type setted when we can, or a operation without
        package in other case.
        MANTLES WILL BE GROUPED INTO PALETES
        """
        res = []
        t_pack = self.env['stock.quant.package']
        op_vals = {
            'location_id': item.sourceloc_id.id,
            'product_id': item.product_id.id,
            'product_uom_id': item.product_uom_id.id,
            'location_dest_id': item.destinationloc_id.id,
            'picking_id': item.transfer_id.picking_id.id,
            'lot_id': item.lot_id.id
        }
        ma_pa = item.product_id.supplier_ma_pa
        ca_ma = item.product_id.supplier_ca_ma
        un_ca = item.product_id.supplier_un_ca

        if pack_type not in ['palet', 'mantle', 'box']:  # Only Units
            op_vals.update({
                'product_qty': num,
            })
            res.append(op_vals)

        elif pack_type == 'mantle':  # Group in a same palet the mantles.
            pack_obj = t_pack.create({'pack_type': 'palet'})
            new_name = pack_obj.name.replace("PACK", 'PALET')
            pack_obj.write({'name': new_name})
            pack_units = ca_ma * un_ca
            op_vals.update({
                'result_package_id': pack_obj.id,
                'product_qty': pack_units * num
            })
            res.append(dict(op_vals))
        else:  # create a different pack and operation if box or palet
            for n in range(num):
                if pack_type == 'palet':
                    pack_units = ma_pa * ca_ma * un_ca
                    pack_name = 'PALET'
                elif pack_type == 'box':
                    pack_units = un_ca
                    pack_name = 'CAJA'
                pack_obj = t_pack.create({'pack_type': pack_type})
                new_name = pack_obj.name.replace("PACK", pack_name)
                pack_obj.write({'name': new_name})
                op_vals.update({
                    'result_package_id': pack_obj.id,
                    'product_qty': pack_units,
                })
                res.append(dict(op_vals))
        return res

    def _get_unit_conversions(self, item):
        """
        Get the expected partition in palets, mantles and units ussing the
        measures of product sheet in suppliers page. (supplier measures).
        It say to us how the products are recived from the supplier
        """
        res = [0, 0, 0, 0]
        prod_obj = item.product_id
        item_qty = item.quantity

        un_ca = prod_obj.supplier_un_ca
        ca_ma = prod_obj.supplier_ca_ma
        ma_pa = prod_obj.supplier_ma_pa

        box_units = un_ca
        mantle_units = un_ca * ca_ma
        palet_units = un_ca * ca_ma * ma_pa

        remaining_qty = item_qty
        int_pal = 0
        int_man = 0
        int_box = 0
        int_units = 0

        while remaining_qty > 0:
            if remaining_qty >= palet_units:
                remaining_qty -= palet_units
                int_pal += 1
            elif remaining_qty >= mantle_units:
                remaining_qty -= mantle_units
                int_man += 1
            elif remaining_qty >= box_units:
                remaining_qty -= box_units
                int_box += 1
            else:
                int_units = remaining_qty
                remaining_qty = 0
        res = [int_pal, int_man, int_box, int_units]
        return res

    def _propose_pack_operations_old(self, item):
        res = []
        int_pal, int_man, int_box, units = self._get_unit_conversions(item)

        if int_pal:
            pa_dics = self._get_pack_type_operation(item, 'palet', int_pal)
            res.extend(pa_dics)
        if int_man:
            ma_dics = self._get_pack_type_operation(item, 'mantle', int_man)
            res.extend(ma_dics)
        if int_box:
            bo_dics = self._get_pack_type_operation(item, 'box', int_box)
            res.extend(bo_dics)
        if units:
            un_dic = self._get_pack_type_operation(item, 'units', units)
            res.extend(un_dic)
        return res
# #############################################################################
# #############################################################################

    def _get_available_location(self):
        """
        Search for a loc with enought volume available and returne_it.
        """
        loc = False
        return loc

    def _propose_pack_operations(self, item):
        """
        Return list of dics with values to create pack operations.
        """
        res = []
        prod_obj = item.product_id
        item_qty = item.quantity

        un_ca = prod_obj.un_ca
        ca_ma = prod_obj.ca_ma
        ma_pa = prod_obj.ma_pa

        box_units = un_ca
        mantle_units = un_ca * ca_ma
        palet_units = un_ca * ca_ma * ma_pa

        remaining_qty = item_qty
        while remaining_qty > 0:
            if remaining_qty >= palet_units:
                # Obtener ubicación donde quepa y mas cercana a picking
                loc_id = self._get_available_location()
                if loc_id:
                    # Crear operación y escribir next_loc_id
                    self.create_pack_operation()
                    remaining_qty -= palet_units
                else:
                    print "Do partition"
            elif remaining_qty >= mantle_units:
                remaining_qty -= mantle_units
            elif remaining_qty >= box_units:
                remaining_qty -= box_units
            else:
                # Crear unidades sueltas a picking directamente??
                remaining_qty = 0
        return res

    @api.one
    def prepare_package_type_operations(self):
        t_pack_op = self.env['stock.pack.operation']
        for op in self.picking_id.pack_operation_ids:
            op.unlink()
        for item in self.item_ids:
            vals_ops = self._propose_pack_operations(item)
            if vals_ops:
                self.picking_id.write({'midban_operations': True})
            for vals in vals_ops:
                t_pack_op.create(vals)
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
