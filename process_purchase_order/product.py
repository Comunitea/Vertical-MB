# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@pexego.es>
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
from openerp import models, api, _
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round


class product_product(models.Model):

    _inherit = "product.product"

    @api.model
    def get_product_supp_record(self, supplier_id):
        res = False
        for supp in self.seller_ids:
            if supp.name.id == supplier_id:
                res = supp
        if not res:
            supp_obj = self.env['res.partner'].browse(supplier_id)
            raise except_orm(_('Error'), _('Supplier %s not defined in product\
                                            supplier list') % supp_obj.name)
        return res

    @api.model
    def get_purchase_unit_ids(self, supplier_id):
        res = []
        supp = self.get_product_supp_record(supplier_id)

        res = []

        if supp.base_use_purchase and supp.log_base_id:
            res.append(supp.log_base_id.id)
        if supp.unit_use_purchase and supp.log_unit_id:
            res.append(supp.log_unit_id.id)
        if supp.box_use_purchase and supp.log_box_id:
            res.append(supp.log_box_id.id)
        return res

    @api.model
    def uom_qty_to_uoc_qty(self, uom_qty, uoc_id, supplier_id):
        """
        Convert product quantity from his default stock unit to the specified
        uoc_id, consulting the conversions in the supplier model.
        """
        supp = self.get_product_supp_record(supplier_id)
        conv = self.get_purchase_unit_conversions(uom_qty, self.uom_po_id.id,
                                                  supplier_id)
        if uoc_id == supp.log_base_id.id:
            return conv['base']
        elif uoc_id == supp.log_unit_id.id:
            return conv['unit']
        elif uoc_id == supp.log_box_id.id:
            return conv['box']

    @api.model
    def get_uom_po_logistic_unit(self, supplier_id):
        supp = self.get_product_supp_record(supplier_id)
        if self.uom_po_id.id == supp.log_base_id.id:
            return 'base'
        elif self.uom_po_id.id == supp.log_unit_id.id:
            return 'unit'
        elif self.uom_po_id.id == supp.log_box_id.id:
            return 'box'
        else:
            raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_po_id.name))

    @api.model
    def get_purchase_unit_conversions(self, qty_uoc, uoc_id, supplier_id):
        #import pdb; pdb.set_trace()
        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0}
        supp = self.get_product_supp_record(supplier_id)

        cte = self._get_unit_ratios(uoc_id, supplier_id) * qty_uoc

        res['base'] = float_round(cte / self._get_unit_ratios(supp.log_base_id.id, supplier_id), 2)
        res['unit'] = float_round(cte / self._get_unit_ratios(supp.log_unit_id.id, supplier_id), 2)
        res['box'] = float_round(cte / self._get_unit_ratios(supp.log_box_id.id, supplier_id), 2)
        return res

    @api.model
    def get_price_conversions(self, qty_uoc, uoc_id, supplier_id):
        #import pdb; pdb.set_trace()
        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0}
        supp = self.get_product_supp_record(supplier_id)

        cte = qty_uoc/self._get_unit_ratios(uoc_id, supplier_id)

        res['base'] = float_round(cte * self._get_unit_ratios(supp.log_base_id.id, supplier_id), 2)
        res['unit'] = float_round(cte * self._get_unit_ratios(supp.log_unit_id.id, supplier_id), 2)
        res['box'] = float_round(cte * self._get_unit_ratios(supp.log_box_id.id, supplier_id), 2)
        return res

    @api.model
    def _conv_units(self, uom_origen, uom_destino, supplier_id):
        #import pdb; pdb.set_trace()
        res = self._get_unit_ratios(uom_origen, supplier_id) / \
              self._get_unit_ratios(uom_destino, supplier_id)
        res = float_round(res,2)
        return res

    @api.model
    def _get_unit_ratios(self, unit, supplier_id):
        #Es funcion devuelve un ratio a la unidad base del producto o uom_id
        #import pdb; pdb.set_trace()
        uom_id = self.uom_id.id
        res = 1

        if supplier_id:
            supp = self.get_product_supp_record(supplier_id)
            kg_un = supp.supp_kg_un or 1.0
            un_ca = supp.supp_un_ca or 1.0
            ca_ma = supp.supp_ca_ma or 1.0
            ma_pa = supp.supp_ma_pa or 1.0

        else:
            #Si no hay supplier id, entonces lo pasamos a unidad base, pero de proveedor.
            supp = self
            kg_un = self.supplier_kg_un or 1.0
            un_ca = self.supplier_un_ca or 1.0
            ca_ma = self.supplier_ca_ma or 1.0
            ma_pa = self.supplier_ma_pa or 1.0

        #Paso todo a la unidad de base
        if unit == supp.log_base_id.id:
            res = 1
        if unit == supp.log_unit_id.id:
            res = kg_un
        if unit == supp.log_box_id.id:
            res = kg_un * un_ca

        #Paso la base a la unidad del producto o uom_id
        if uom_id == supp.log_base_id.id:
            res = res
        if uom_id == supp.log_unit_id.id:
            res = res / kg_un
        if uom_id == supp.log_box_id.id:
            res = res / (kg_un * un_ca)

        res = float_round(res,2)
        return res

    @api.model
    def get_uom_uoc_prices(self, uoc_id, supplier_id, custom_price_unit=0.0,
                           custom_price_udc=0.0):

        import pdb; pdb.set_trace()#
        custom_price_udc_from_unit = 0.0
        custom_price_unit_from_udc = 0.0
        supp = self.get_product_supp_record(supplier_id)
        #Para evitar si hay custom_price_udc, lo pasamos a custom_price_unit
        if custom_price_udc:
            #si hay lo pasamos a custom price unit para no andar con if
            custom_price_unit_from_udc = self._conv_units( self.uom_id.id,uoc_id, supplier_id) * custom_price_udc

        elif custom_price_unit:
            #si hay lo pasamos a sacamos custom price udc
            custom_price_udc_from_unit = self._conv_units(uoc_id, self.uom_id.id,  supplier_id) * custom_price_unit

        else:
            price_unit = self.standard_price
            price_udc =  self._conv_units(uoc_id, self.uom_id.id, supplier_id) * price_unit

        price_udc = custom_price_udc or custom_price_udc_from_unit or price_udc
        price_udc = float_round (price_udc,2)
        price_unit = custom_price_unit or custom_price_unit_from_udc or price_unit
        price_unit = float_round(price_unit,2)

        return price_unit, price_udc

class ProductUom(models.Model):

    _inherit = 'product.uom'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only allowed products for a product
            if product_id is in context."""
        if context is None:
            context = {}
        if context.get('supp_product_id', False) and context.get('supplier_id',
                                                                 False):
            t_prod = self.pool.get('product.product')
            prod = t_prod.browse(cr, uid, context['supp_product_id'], context)
            prod_udc_ids = prod.get_purchase_unit_ids(context['supplier_id'])
            # Because sometimes args = [category = False]
            args = [['id', 'in', prod_udc_ids]]
        return super(ProductUom, self).search(cr, uid, args,
                                              offset=offset,
                                              limit=limit,
                                              order=order,
                                              context=context,
                                              count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        res = super(ProductUom, self).name_search(name, args=args,
                                                  operator=operator,
                                                  limit=limit)
        if self._context.get('supp_product_id', False) and \
                self._context.get('supplier_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            res = recs.name_get()

        return res
