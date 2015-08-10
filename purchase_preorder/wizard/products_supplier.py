# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Kiko Sánchez$ <kiko@comunitea.com>
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

from openerp import models, api, fields, _

import openerp.addons.decimal_precision as dp


import time


class ProductsSupplier(models.Model):

    _inherit='products.supplier'

    @api.one
    def _get_tm(self):
        self.tm = time.time()

    supplier_id = fields.Many2one(related = "preorder_id.supplier_id")
    product_uoc_qty = fields.Float('Quantity (UdC)',
                               digits_compute=dp.
                               get_precision('Product Unit of Measure'))
    product_qty = fields.Float('Quantity',
                               digits_compute=dp.
                               get_precision('Product Unit of Measure'))
    product_uoc = fields.Many2one('product.uom', 'Unit of Buy')
    supplier_uoc = fields.Char('Supplier Unidad de Compra')
    test = fields.Boolean()
    kgrs = fields.Float ("Quantity Kgrs")
    tm = fields.Float ('TM', compute = _get_tm)
    last_tm = fields.Float ('Last TM')


    @api.model
    @api.onchange ('product_uoc')
    def _check_product_uoc(self):

        import pdb; pdb.set_trace()
        product_id = self.product_id
        supplier_id = self.supplier_id
        uoc_id = self.product_uoc.id

        supp = product_id.get_product_supp_record(supplier_id.id)
        conv = product_id.get_purchase_price_conversions(
                                            product_id.standard_price,
                                            product_id.uom_id.id,
                                            self.supplier_id.id)

        if uoc_id == supp.log_base_id.id:
            self.price_purchase = conv['base']
        elif uoc_id == supp.log_unit_id.id:
            self.price_purchase = conv['unit']
        elif uoc_id == supp.log_box_id.id:
           self.price_purchase = conv['box']

        ctx = dict(self._context)
        ctx.update({
           'change': 'product_uoc_qty'
           })
        self.with_context(ctx)._check_qtys()

        return


    @api.model
    @api.onchange ('palets', 'mantles', 'boxes', 'product_uoc_qty')
    def _check_qtys(self):

        if self.last_tm == self._context['tm']:
            return
        #import pdb; pdb.set_trace()
        flag = self._context['change']
        uom_id = self.product_uoc.id
        if flag == "palets" or flag == 'mantles' or flag =='boxes':
            pool_uom =  self.env['product.uom'].search([('like_type','=', flag), ('active', '=', False)])
            if pool_uom:
                uom_id = pool_uom[0].id

        product_id = self.product_id
        supplier_id = self.supplier_id
        uoc_id = self.product_uoc.id
        conv = product_id.get_purchase_unit_conversions(self[flag],
                                                        uom_id,
                                                        self.supplier_id.id)

        self.kgrs = conv['base']
        self.unitskg = conv['unit']
        self.boxes = conv['boxes']
        self.mantles = conv['mantles']
        self.palets = conv['palets']
        self.product_qty = conv['stock']

        supp = product_id.get_product_supp_record(supplier_id.id)
        if uoc_id == supp.log_base_id.id:
            self.product_uoc_qty = conv['base']
        elif uoc_id == supp.log_unit_id.id:
            self.product_uoc_qty = conv['unit']
        elif uoc_id == supp.log_box_id.id:
            self.product_uoc_qty = conv['box']

        self.last_tm = self._context['tm']

        return





