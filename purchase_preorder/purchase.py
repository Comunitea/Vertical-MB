# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
import openerp.addons.decimal_precision as dp


class purchase_order_line(osv.Model):
    _inherit = 'purchase.order.line'

    def _calc_uoms(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        mod_obj = self.pool.get('ir.model.data')
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'palets': 0.0,
                'mantles': 0.0,
                'boxes': 0.0,
            }
            boxes = mantles = palets = 0.0
            unit_uom = mod_obj.get_object_reference(cr,
                                                    uid,
                                                    'product',
                                                    'product_uom_unit')
            unit_id = unit_uom and unit_uom[1] or False
            if line.product_qty and line.product_uom.id == unit_id:
                un_ca = line.product_id.supplier_un_ca
                ca_ma = line.product_id.supplier_ca_ma
                ma_pa = line.product_id.supplier_ma_pa
                boxes = round(un_ca and (line.product_qty / un_ca) or 0.0, 2)
                mantles = round(ca_ma and (boxes / ca_ma) or 0.0, 2)
                palets = round(ma_pa and (mantles / ma_pa) or 0.0, 2)

            res[line.id]['boxes'] = boxes
            res[line.id]['mantles'] = mantles
            res[line.id]['palets'] = palets
        return res

    _columns = {
        'palets': fields.function(_calc_uoms,
                                  digits_compute=dp.get_precision('Account'),
                                  string='Palets',
                                  store=True,
                                  multi="sums",
                                  readonly=True),
        'mantles': fields.function(_calc_uoms,
                                   digits_compute=dp.get_precision('Account'),
                                   string='Mantles',
                                   store=True,
                                   multi="sums",
                                   readonly=True),
        'boxes': fields.function(_calc_uoms,
                                 digits_compute=dp.get_precision('Account'),
                                 string='Boxes',
                                 store=True,
                                 multi="sums",
                                 readonly=True),
    }


class purchase_order(osv.Model):
    _inherit = 'purchase.order'
    _columns = {
        'preorder_id': fields.many2one('purchase.preorder',
                                       'PreOrder')
    }
