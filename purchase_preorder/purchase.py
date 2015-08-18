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
            un_ca = ca_ma = ma_pa = 1.0
            boxes = mantles = palets = 0.0

            unit_uom = mod_obj.get_object_reference(cr,
                                                    uid,
                                                    'product',
                                                    'product_uom_unit')
            supplier_id = line.order_id.partner_id
            product_id = line.product_id

            suppinfo = self.pool.get('product.supplierinfo').\
                search(cr, uid,[('product_tmpl_id', '=', product_id.id)
                , ('name', '=', supplier_id.id)])
            supp = self.pool.get('product.supplierinfo').browse(cr, uid,
                                                                suppinfo)
            if supp:
                un_ca = supp.supp_un_ca
                ca_ma = supp.supp_ca_ma
                ma_pa = supp.supp_ma_pa

            #Buscamos cajas
            conv = product_id.\
                get_purchase_unit_conversions(line.product_uoc_qty,
                                              line.product_uoc.id,
                                              supplier_id.id)

            # unit_id = unit_uom and unit_uom[1] or False
            # if line.product_qty and line.product_uom.id == unit_id:
            #     units = line.product_qty
            #     boxes = round(un_ca and (units / un_ca) or 0.0, 2)
            #     mantles = round(ca_ma and (boxes / ca_ma) or 0.0, 2)
            #     palets = round(ma_pa and (mantles / ma_pa) or 0.0, 2)

            res[line.id]['boxes'] = conv['box']
            res[line.id]['mantles'] = round(ca_ma and (conv['box'] / ca_ma) or 0.0, 2)
            res[line.id]['palets'] = round(ma_pa and (conv['box'] / (ca_ma * ma_pa)) or 0.0, 2)

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