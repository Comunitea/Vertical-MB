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
from openerp.tools.float_utils import float_round

import time


class ProductsSupplier(models.Model):

    _inherit='products.supplier'

    @api.one
    def _get_tm(self):
        self.tm = time.time()

    supplier_id = fields.Many2one(related = "preorder_id.supplier_id")
    product_uoc_qty = fields.Float('Quantity (UdC)',
                               digits_compute=dp.
                               get_precision('Product Unit of Measure'),
                               )
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
<<<<<<< HEAD
=======
        #import pdb; pdb.set_trace()
>>>>>>> 4b58242c4079c7b5335f916bd87ac637ddd48c1b
        product_id = self.product_id
        supplier_id = self.supplier_id

        #'primero cantidades'
        self._check_uoc_qty()
        #luego los precios
        unit_ratios = product_id._get_unit_ratios(self.product_uoc.id, supplier_id.id)
        self.price_purchase =  product_id.standard_price * unit_ratios


    @api.model
    def _conv_boxes_logis (self, flag):
        # Convierte de product_uoc a mantles o palets
        product_id = self.product_id
        supplier_id = self.supplier_id
        supp = product_id.get_product_supp_record(supplier_id.id)
        res = 1
        if flag == "mantles":
            cte = supp.supp_ca_ma or 1.0
            res = product_id._conv_units(self.product_uoc.id,supp.log_box_id.id, supplier_id.id) / cte
        if flag == "palets":
            cte = supp.supp_ca_ma * supp.supp_ma_pa or 1.0
            res =  product_id._conv_units( self.product_uoc.id,  supp.log_box_id.id, supplier_id.id) / cte
        return res

    @api.model
    @api.onchange('product_uoc_qty')
    def _check_uoc_qty(self):

        #import pdb; pdb.set_trace()
        if self.last_tm == self._context['tm']:
            return
        self.last_tm = self._context['tm']

        mantles = self._conv_boxes_logis('mantles') * self.product_uoc_qty
        palets =  self._conv_boxes_logis('palets') * self.product_uoc_qty

        self.mantles = float_round(mantles,2)
        self.palets = float_round(palets,2)
        product_id = self.product_id
        self.product_qty = product_id._conv_units(self.product_uoc.id, product_id.uom_id.id, self.supplier_id.id)
        supplier_id = self.supplier_id
        supp = product_id.get_product_supp_record(supplier_id.id)
        self.boxes = self.mantles * supp.supp_ca_ma
        self.unitskg = self.product_uoc_qty
        return





    @api.model
    @api.onchange ('palets', 'mantles')
    def _check_qtys(self):
        if self.last_tm == self._context['tm']:
            return
        self.last_tm = self._context['tm']

        flag = self._context['change']
        product_id = self.product_id
        supplier_id = self.supplier_id
        supp = product_id.get_product_supp_record(supplier_id.id)

        if flag == 'palets':
            self.mantles = float_round(self.palets * supp.supp_ma_pa,2 )
            cte_boxes = 1 / self._conv_boxes_logis(flag)
            self.product_uoc_qty = float_round(self.palets * cte_boxes,2)

        if flag == 'mantles':
            self.palets = float_round(self.mantles / supp.supp_ma_pa ,2 )
            cte_boxes = 1 / self._conv_boxes_logis(flag)
            self.product_uoc_qty = float_round(self.mantles * cte_boxes ,2)

        self.boxes = self.mantles * supp.supp_ca_ma
        self.product_qty = product_id._conv_units(self.product_uoc.id, product_id.uom_id.id, self.supplier_id.id)
        self.unitskg = self.product_uoc_qty
        return
