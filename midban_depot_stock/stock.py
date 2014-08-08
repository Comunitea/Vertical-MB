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
            'product_id': op.product_id.id,
            'product_uom_id': op.product_uom_id.id,
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
            pa_dics = self._get_pack_type_operation(cr, uid, ids, op, 'palete',
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
                            bo_dics = self._get_pack_type_operation(cr, uid,
                                                                    ids, op,
                                                                    'box',
                                                                    int_box,
                                                                    context=
                                                                    context)
                            res.extend(bo_dics)
                            if dec_box != 0:  # Get operations for units
                                units = prod_obj.supplier_un_ca * dec_box
                                un_dic = self._get_pack_type_operation(cr,
                                                                       uid,
                                                                       ids, op,
                                                                       'units',
                                                                       units,
                                                                       context=
                                                                       context)
                                res.extend(un_dic)

                        else:  # ubicate the rest of units
                            units = prod_obj.supplier_un_ca * num_box
                            un_dics = self._get_pack_type_operation(cr, uid,
                                                                    ids, op,
                                                                    'units',
                                                                    units,
                                                                    context=
                                                                    context)
                            res.extend(un_dics)
                else:  # Ubicate Boxes
                    num_box = prod_obj.supplier_ca_ma * num_mant
                    if num_box >= 1:  # Get boxes and maybe some units
                        int_box = int(num_box)
                        dec_box = abs(num_box) - abs(int(num_box))
                        bo_dics = self._get_pack_type_operation(cr, uid,
                                                                ids, op,
                                                                'box',
                                                                int_box,
                                                                context=
                                                                context)
                        res.extend(bo_dics)
                        if dec_box != 0:  # Get operations for units
                            units = prod_obj.supplier_un_ca * dec_box
                            un_dics = self._get_pack_type_operation(cr, uid,
                                                                    ids, op,
                                                                    'units',
                                                                    units,
                                                                    context=
                                                                    context)
                            res.extend(un_dics)
                    else:  # Ubicate the rest of units
                        units = prod_obj.supplier_un_ca * num_box
                        un_dics = self._get_pack_type_operation(cr, uid,
                                                                ids, op,
                                                                'units',
                                                                units,
                                                                context=
                                                                context)
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
                num_box = prod_obj.supplier_ca_ma * num_mant
                if num_box >= 1:  # Get boxes and maybe some units
                    int_box = int(num_box)
                    dec_box = abs(num_box) - abs(int(num_box))
                    bo_dics = self._get_pack_type_operation(cr, uid,
                                                            ids, op,
                                                            'box',
                                                            int_box,
                                                            context=
                                                            context)
                    res.extend(bo_dics)
                    if dec_box != 0:  # Get operations for units
                        units = prod_obj.supplier_un_ca * dec_box
                        un_dics = self._get_pack_type_operation(cr, uid,
                                                                ids, op,
                                                                'units',
                                                                units,
                                                                context=
                                                                context)
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
            for op in pick.pack_operation_ids:
                vals_ops = self._propose_pack_operations(cr, uid, ids, op,
                                                         context=context)
                #  If val_ ops:  #  Indent to get default operations # TODO?
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
    }


class stock_pack_operation(osv.osv):
    _inherit = "stock.pack.operation"

    def _get_location(self, cr, uid, prod_obj, wh_obj, pack_type,
                      context=None):
        """
        For a product, choose between put it in picking zone (if it is empty
        and no older reference stored in storage zone or put it in closest
        storage zone to product picking location
        """
        location_id = False

        return location_id

    def change_location_dest_id(self, cr, uid, operations, wh_obj,
                                context=None,):
        """
        Change the storage location for a specific one
        """
        if context is None:
            context = {}
        res = {}
        for ops in operations:
            # import ipdb; ipdb.set_trace()
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
            location_id = self._get_location(cr, uid, prod_obj, wh_obj,
                                             ops.pack_type, context=context)
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

    _columns = {
        'pack_type': fields.function(_get_pack_type, type='char',
                                     string='Pack Type', readonly=True),
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
    _columns = {
        'width': fields.float('Width',
                              digits_compute=
                              dp.get_precision('Product Price')),
        'height': fields.float('Height',
                               digits_compute=
                               dp.get_precision('Product Price')),
        # 'available_height': fields.float('Available Height',
        #                                  digits_compute=
        #                                  dp.get_precision('Product Price')),
        'length': fields.float('Lenght',
                               digits_compute=
                               dp.get_precision('Product Price')),
        # 'volume': fields.float('Volume',
        #                        digits_compute=
        #                        dp.get_precision('Product Price')),
        # 'available_volume': fields.float('Available Volume',
        #                                  digits_compute=
        #                                  dp.get_precision('Product Price')),
        'storage_type': fields.selection([('standard', 'Standard'),
                                         ('boxes', 'Boxes'),
                                         ('mantles', 'Mantles'),
                                         ('palets', 'Palets')],
                                         'Storage Type'),
        # 'ref': fields.char("Reference", size=64),
    }
    _defaults = {
        'storage_type': 'standard',
        # 'available_height': -1,
        # 'available_volume': -1,
    }
    _sql_constraints = [
        ('name_uniq', 'unique(storage_type)',
         _("Field Storage type must be unique!"))
    ]

    def onchange_storage_type(self, cr, uid, ids, location_type, context=None):
        """ Avoid set manually a storage type of mantles or palets"""
        if context is None:
            context = {}
        res = {'value': {}}
        if location_type in ['mantles', 'palets']:
            res['warning'] = {'title': _('Warning!'),
                              'message': _("This type can be only managed by\
                                            the task schedule")}
            res['value']['storage_type'] = 'standard'
        return res
