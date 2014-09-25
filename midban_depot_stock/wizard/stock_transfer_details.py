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
# from openerp import models, fields, api
# from openerp.tools.translate import _
# import openerp.addons.decimal_precision as dp
# from datetime import datetime


def _reopen(self, res_id, model):
    return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': res_id,
            'res_model': self._name,
            'target': 'new',
            # save original model in context, because selecting the list of
            #available templates requires a model in context
            'context': {
                'default_model': model,
            },
            }


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    midban_operations = fields.Boolean(string='Custom midban operations',
                                       related=
                                       'picking_id.midban_operations',
                                       readonly=True)
    picking_type_code = fields.Char('Picking code', related=
                                    'picking_id.picking_type_code')

    def _get_unit_conversions(self, item_obj):
        res = {
            'units': 0.0,
            'boxes': 0.0,
            'mantles': 0.0,
            'palets': 0.0,
        }
        unit_type = item_obj.product_uom_id.like_type or 'units'
        un_ca = item_obj.product_id.supplier_un_ca
        ca_ma = item_obj.product_id.supplier_ca_ma
        ma_pa = item_obj.product_id.supplier_ma_pa
        qty = item_obj.quantity
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

    def _get_pack_type_operation(self, item, pack_type, num):
        """
        Return a dictionary containing the values to create a pack operation
        with pack and his pack type setted when we can, or a operation without
        package in other case.
        """
        res = []
        t_pack = self.env['stock.quant.package']
        # item_vals = {
        #     'transfer_id': item.transfer_id.id,
        #     'product_id': item.product_id.id,
        #     'product_uom_id': item.product_uom_id.id,
        #     'quantity': 0,  # To set
        #     'package_id': False,
        #     'lot_id': item.lot_id.id,
        #     'sourceloc_id': item.sourceloc_id.id,
        #     'destinationloc_id': item.destinationloc_id.id,
        #     'result_package_id': False,  # To set
        #     'date': item.date if item.date else datetime.now(),
        #     'owner_id': item.owner_id.id,
        # }
        op_vals = {
            'location_id': item.sourceloc_id.id,
            'product_id': item.product_id.id,
            'product_uom_id': item.product_uom_id.id,
            'location_dest_id': item.destinationloc_id.id,
            'picking_id': item.transfer_id.picking_id.id,
            'lot_id': item.lot_id.id
        }
        if pack_type not in ['palet', 'mantle', 'box']:
            # item_vals.update({
            #     'quantity': num,
            # })
            # res.append(item_vals)
            op_vals.update({
                'product_qty': num,
            })
            res.append(op_vals)
        else:
            for n in range(num):
                ma_pa = item.product_id.supplier_ma_pa
                ca_ma = item.product_id.supplier_ca_ma
                un_ca = item.product_id.supplier_un_ca
                if pack_type == 'palet':
                    pack_units = ma_pa * ca_ma * un_ca
                    pack_name = 'PALET'
                elif pack_type == 'mantle':
                    pack_units = ca_ma * un_ca
                    pack_name = 'MANTO'
                elif pack_type == 'box':
                    pack_units = un_ca
                    pack_name = 'CAJA'
                pack_obj = t_pack.create({'pack_type': pack_type})
                new_name = pack_obj.name.replace("PACK", pack_name)
                pack_obj.write({'name': new_name})
                # item_vals.update({
                #     'result_package_id': pack_obj.id,
                #     'quantity': pack_units,
                # })
                # res.append(dict(item_vals))
                op_vals.update({
                    'result_package_id': pack_obj.id,
                    'product_qty': pack_units,
                })
                res.append(dict(op_vals))
        return res

    def _get_unit_conversions2(self, item):
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

    def _propose_pack_operations2(self, item):
        res = []
        # import ipdb
        # ipdb.set_trace()
        int_pal, int_man, int_box, units = self._get_unit_conversions2(item)

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

    def _propose_pack_operations(self, item):
        res = []
        # import ipdb
        # ipdb.set_trace()
        prod_obj = item.product_id
        conv = self._get_unit_conversions(item)
        if conv['palets'] >= 1:
            palets = conv['palets']
            int_pal = int(palets)
            dec_pal = abs(palets) - abs(int(palets))
            pa_dics = self._get_pack_type_operation(item, 'palet', int_pal)
            res.extend(pa_dics)
            if dec_pal != 0:  # Get a integer number of mantles or boxes
                num_mant = prod_obj.supplier_ma_pa * dec_pal
                if num_mant >= 1:  # Get mantles and maybe some boxes
                    int_man = int(num_mant)
                    dec_man = abs(num_mant) - abs(int(num_mant))
                    ma_dics = self._get_pack_type_operation(item, 'mantle',
                                                            int_man)
                    res.extend(ma_dics)
                    if dec_man != 0:  # Ubicate boxes
                        num_box = prod_obj.supplier_ca_ma * dec_man
                        if num_box >= 1:  # Get boxes and maybe some units
                            int_box = int(num_box)
                            dec_box = abs(num_box) - abs(int(num_box))
                            bo_dics = self._get_pack_type_operation(item,
                                                                    'box',
                                                                    int_box)
                            res.extend(bo_dics)
                            if dec_box != 0:  # Get operations for units
                                units = prod_obj.supplier_un_ca * dec_box
                                un_dic = self._get_pack_type_operation(item,
                                                                       'units',
                                                                       units)
                                res.extend(un_dic)

                        else:  # ubicate the rest of units
                            units = prod_obj.supplier_un_ca * num_box
                            un_dics = self._get_pack_type_operation(item,
                                                                    'units',
                                                                    units)
                            res.extend(un_dics)
                else:  # Ubicate Boxes
                    num_box = prod_obj.supplier_ca_ma * num_mant
                    if num_box >= 1:  # Get boxes and maybe some units
                        int_box = int(num_box)
                        dec_box = abs(num_box) - abs(int(num_box))
                        bo_dics = self._get_pack_type_operation(item, 'box',
                                                                int_box)
                        res.extend(bo_dics)
                        if dec_box != 0:  # Get operations for units
                            units = prod_obj.supplier_un_ca * dec_box
                            un_dics = self._get_pack_type_operation(item,
                                                                    'units',
                                                                    units)
                            res.extend(un_dics)
                    else:  # Ubicate the rest of units
                        units = prod_obj.supplier_un_ca * num_box
                        un_dics = self._get_pack_type_operation(item, 'units',
                                                                units)
                        res.extend(un_dics)

        elif conv['mantles'] >= 1:
            mantles = conv['mantles']
            int_man = int(mantles)
            dec_man = abs(mantles) - abs(int(mantles))
            ma_dics = self._get_pack_type_operation(item, 'mantle', int_man)
            res.extend(ma_dics)
            if dec_man != 0:  # Ubicate boxes
                num_box = prod_obj.supplier_ca_ma * dec_man
                if num_box >= 1:  # Get boxes and maybe some units
                    int_box = int(num_box)
                    dec_box = abs(num_box) - abs(int(num_box))
                    bo_dics = self._get_pack_type_operation(item, 'box',
                                                            int_box)
                    res.extend(bo_dics)
                    if dec_box != 0:  # Get operations for units
                        units = prod_obj.supplier_un_ca * dec_box
                        un_dics = self._get_pack_type_operation(item, 'units',
                                                                units)
                        res.extend(un_dics)

        elif conv['boxes'] > 0:
            boxes = conv['boxes']
            int_box = int(boxes)
            dec_box = abs(boxes) - abs(int(boxes))
            bo_dics = self._get_pack_type_operation(item, 'box', int_box)
            res.extend(bo_dics)
            if dec_box != 0:  # Get operations for units
                units = prod_obj.supplier_un_ca * dec_box
                un_dics = self._get_pack_type_operation(item, 'units', units)
                res.extend(un_dics)

        else:
            units = conv['units']
            un_dics = self._get_pack_type_operation(item, 'units', units)
            res.extend(un_dics)

        return res

    @api.one
    def prepare_package_type_operations(self):
        t_pack_op = self.env['stock.pack.operation']
        for op in self.picking_id.pack_operation_ids:
            op.unlink()
        for item in self.item_ids:
            # retornaba los links para que se vieran en la misma ventana de los
            # nuevos links, pero hay que reabrir el wizard y no se como se hace
            # con el _reopen quizás se pueda, (buscar ejem)
            # item_vals = self._proposepack_operations(item)
            # item.unlink()
            # for vals in item_vals:
            #     # vals['transfer_id'] = created_id.id
            #     t_operations.create(vals)
            vals_ops = self._propose_pack_operations2(item)
            if vals_ops:
                self.picking_id.write({'midban_operations': True})
            for vals in vals_ops:
                t_pack_op.create(vals)
        # return _reopen(self, self.id, self._name)
        return True
