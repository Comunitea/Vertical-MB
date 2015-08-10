# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 COmunitea Servicios Tecnológicos All Rights Reserved
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
from openerp import models, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round


class product_product(models.Model):

    _inherit = "product.product"



    @api.model
    def get_purchase_price_conversions(self, qty_uoc, uoc_id, supplier_id):

        import pdb; pdb.set_trace()
        #por si hace falta precio de manteles o palets
        #import pdb; pdb.set_trace()

        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0,
               'prov': 0.0,
               'mantles' : 0.0,
               'palets' : 0.0,
               'stock' : 0.0}

        supp = self.get_product_supp_record(supplier_id)
        #uom = self.env['product.uom'].browse ([(uoc_id)])
        product_uom_id = self.env['product.template'].browse([(self.id)]).uom_id.id
        uom_id = product_uom_id
        product_uom_po_id = self.env['product.template'].browse([(self.id)]).uom_po_id.id
        if uom_id == supp.log_base_id.id:
            res['base'] = qty_uoc
            res['unit'] = float_round(res['base'] * supp.supp_kg_un, 2)
            res['box'] = float_round(res['unit'] * supp.supp_un_ca, 2)
            res['mantles'] =  float_round(res['box'] * supp.supp_ca_ma, 2)
            res['palets'] =  float_round(res['mantles'] * supp.supp_ca_ma, 2)
        elif uom_id == supp.log_unit_id.id:
            res['unit'] = qty_uoc
            res['box'] = float_round(res['unit'] * supp.supp_un_ca, 2)
            res['base'] = float_round(res['unit'] / supp.supp_kg_un, 2)
            res['mantles'] =  float_round(res['box'] * supp.supp_ca_ma, 2)
            res['palets'] =  float_round(res['mantles'] * supp.supp_ca_ma, 2)
        elif uom_id == supp.log_box_id.id:
            res['box'] = qty_uoc
            res['unit'] = float_round(res['box'] / supp.supp_un_ca, 2)
            res['base'] = float_round(res['unit'] / supp.supp_kg_un, 2)
            res['mantles'] =  float_round(res['box'] * supp.supp_ca_ma, 2)
            res['palets'] =  float_round(res['mantles'] * supp.supp_ma_pa, 2)


        #res['prov'] es la cantidad en la unidad de medida del proveedor
        if product_uom_po_id == supp.log_base_id.id:
            res['prov']=res['base']
        elif product_uom_po_id == supp.log_unit_id.id:
            res['prov']=res['unit']
        elif product_uom_po_id == supp.log_box_id.id:
            res['prov']=res['box']
        else:
            raise except_orm(_('Error'), _('Product uom_po not defined in %s') % self.name)

        #res['stock'] es la cantidad en unidaddes de stock
        if product_uom_id == supp.log_base_id.id:
            res['stock']=res['base']
        elif product_uom_id == supp.log_unit_id.id:
            res['stock']=res['unit']
        elif product_uom_id == supp.log_box_id.id:
            res['stock']=res['box']
        else:
            raise except_orm(_('Error'), _('Product uom not defined in %s') % self.name)

        if uoc_id== supp.log_base_id.id:
            res['udc']=res['base']
        elif uoc_id == supp.log_unit_id.id:
            res['udc']=res['unit']
        elif uoc_id == supp.log_box_id.id:
            res['udc']=res['box']
        else:
            raise except_orm(_('Error'), _('Product uom not defined in %s') % self.name)
        return res


    @api.model
    def get_purchase_unit_conversions(self, qty_uoc, uoc_id, supplier_id):

        #import pdb; pdb.set_trace()

        # ampliamos para que res devuelva más valores
        # conversiones a todas las unidades de medida
        #

        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0,
               'prov': 0.0,
               'mantles' : 0.0,
               'palets' : 0.0 }

        supp = self.get_product_supp_record(supplier_id)
        uom = self.env['product.uom'].browse ([(uoc_id)])
        product_uom_id = self.env['product.template'].browse([(self.id)]).uom_id.id
        product_uom_po_id = self.env['product.template'].browse([(self.id)]).uom_po_id.id

        #mantles, palets and boxes only in preorder
        if uom.like_type == 'mantles':
            res['mantles'] = qty_uoc
            res['palets'] =  float_round(res['mantles'] / supp.supp_ma_pa, 2)
            res['box'] =  float_round(res['mantles'] * supp.supp_ca_ma, 2)
            res['unit'] = float_round(res['box'] * supp.supp_un_ca, 2)
            res['base'] = float_round(res['unit'] * supp.supp_kg_un, 2)
        elif uom.like_type == 'palets':
            res['palets'] = qty_uoc
            res['mantles'] =  float_round(res['palets'] * supp.supp_ma_pa, 2)
            res['box'] =  float_round(res['mantles'] * supp.supp_ca_ma, 2)
            res['unit'] = float_round(res['box'] * supp.supp_un_ca, 2)
            res['base'] = float_round(res['unit'] * supp.supp_kg_un, 2)
        elif uoc_id == supp.log_base_id.id:
            res['base'] = qty_uoc
            res['unit'] = float_round(res['base'] / supp.supp_kg_un, 2)
            res['box'] = float_round(res['unit'] / supp.supp_un_ca, 2)
            res['mantles'] =  float_round(res['box'] / supp.supp_ca_ma, 2)
            res['palets'] =  float_round(res['mantles'] / supp.supp_ma_pa, 2)
        elif uoc_id == supp.log_unit_id.id:
            res['unit'] = qty_uoc
            res['base'] = float_round(res['unit'] * supp.supp_kg_un, 2)
            res['box'] = float_round(res['unit'] / supp.supp_un_ca, 2)
            res['mantles'] =  float_round(res['box'] / supp.supp_ca_ma, 2)
            res['palets'] =  float_round(res['mantles'] / supp.supp_ma_pa, 2)
        elif uoc_id == supp.log_box_id.id:
            res['box'] = qty_uoc
            res['unit'] = float_round(res['box'] * supp.supp_un_ca, 2)
            res['base'] = float_round(res['unit'] * supp.supp_kg_un, 2)
            res['mantles'] =  float_round(res['box'] / supp.supp_ca_ma, 2)
            res['palets'] =  float_round(res['mantles'] / supp.supp_ma_pa, 2)

        #siempre. la 3 unidad de compra es siempre boxes, independiente del nombre
        res['boxes'] = res['box']

        #res['prov'] es la cantidad en la unidad de medida del proveedor
        if product_uom_po_id == supp.log_base_id.id:
            res['prov']=res['base']
        elif product_uom_po_id == supp.log_unit_id.id:
            res['prov']=res['unit']
        elif product_uom_po_id == supp.log_box_id.id:
            res['prov']=res['box']
        else:
            raise except_orm(_('Error'), _('Product uom_po not defined in %s') % self.name)

        #res['stock'] es la cantidad en unidaddes de stock
        if product_uom_id == supp.log_base_id.id:
            res['stock']=res['base']
        elif product_uom_id == supp.log_unit_id.id:
            res['stock']=res['unit']
        elif product_uom_id == supp.log_box_id.id:
            res['stock']=res['box']
        else:
            raise except_orm(_('Error'), _('Product uom not defined in %s') % self.name)


        return res


    @api.model
    def get_uom_uoc_prices(self, uoc_id, supplier_id, custom_price_unit=0.0,
                           custom_price_udc=0.0):
        import pdb; pdb.set_trace()#
        supp = self.get_product_supp_record(supplier_id)
        if custom_price_udc:
            price_udc = custom_price_udc
            log_unit = self.get_uom_po_logistic_unit(supplier_id)
            if uoc_id == supp.log_base_id.id:
                if log_unit == 'base':
                    price_unit = price_udc
                if log_unit == 'unit':
                    price_unit = price_udc * supp.supp_kg_un
                if log_unit == 'box':
                    price_unit = price_udc * supp.supp_kg_un * supp.supp_.un_ca
                price_unit = price_unit
            elif uoc_id == supp.log_unit_id.id:
                if log_unit == 'base':
                    price_unit = float_round(price_udc / supp.supp_kg_un, 2)
                if log_unit == 'unit':
                    price_unit = price_udc
                if log_unit == 'box':
                    price_unit = price_udc * supp.supp_un_ca
            elif uoc_id == supp.log_box_id.id:
                if log_unit == 'base':
                    price_unit = \
                        float_round(
                            price_udc / (supp.supp_kg_un * supp.supp_un_ca), 2)
                if log_unit == 'unit':
                    price_unit = float_round(price_udc / supp.supp_un_ca, 2)
                if log_unit == 'box':
                    price_unit = price_udc

        else:
            price_unit = custom_price_unit or self.standard_price
            price_udc = 0.0
            log_unit = self.get_uom_po_logistic_unit(supplier_id)
            if uoc_id == supp.log_base_id.id:
                if log_unit == 'base':
                    price_udc = price_unit
                if log_unit == 'unit':
                    price_udc = price_unit / supp.supp_kg_un
                if log_unit == 'box':
                    price_udc = price_unit * supp.supp_kg_un * supp.supp_un_ca

            elif uoc_id == supp.log_unit_id.id:
                if log_unit == 'base':
                    price_udc = float_round(price_unit * supp.supp_kg_un, 2)
                if log_unit == 'unit':
                    price_udc = price_unit
                if log_unit == 'box':
                    price_udc = price_unit / supp.supp_un_ca

            elif uoc_id == supp.log_box_id.id:
                if log_unit == 'base':
                    price_udc = \
                        float_round(price_unit * supp.supp_kg_un *
                                    supp.supp_un_ca, 2)
                if log_unit == 'unit':
                    price_udc = float_round(price_unit * supp.supp_un_ca, 2)
                if log_unit == 'box':
                    price_udc = price_unit
        return price_unit, price_udc


    @api.model
    def get_uom_po_logistic_unit(self, supplier_id):
        supp = self.get_product_supp_record(supplier_id)
        if self.uom_id.id == supp.log_base_id.id:
            return 'base'
        elif self.uom_id.id == supp.log_unit_id.id:
            return 'unit'
        elif self.uom_id.id == supp.log_box_id.id:
            return 'box'
        else:
            raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_po_id.name))