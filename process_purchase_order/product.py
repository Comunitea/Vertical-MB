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
from openerp import models, api
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
    def get_purchase_unit_conversions(self, qty_uoc, uoc_id, supplier_id):
        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0}
        supp = self.get_product_supp_record(supplier_id)
        if uoc_id == supp.log_base_id.id:
            res['base'] = qty_uoc
            res['unit'] = float_round(res['base'] / supp.supp_kg_un, 2)
            res['box'] = float_round(res['unit'] / supp.supp_un_ca, 2)
        elif uoc_id == supp.log_unit_id.id:
            res['unit'] = qty_uoc
            res['box'] = float_round(res['unit'] / supp.supp_un_ca, 2)
            res['base'] = float_round(res['unit'] * supp.supp_kg_un, 2)
        elif uoc_id == supp.log_box_id.id:
            res['box'] = qty_uoc
            res['unit'] = float_round(res['box'] * supp.supp_un_ca, 2)
            res['base'] = float_round(res['unit'] * supp.supp_kg_un, 2)
        return res

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
    def get_uom_uoc_prices(self, uoc_id, supplier_id, custom_price_unit=0.0,
                           custom_price_udc=0.0):
        # import ipdb; ipdb.set_trace()
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
            price_unit = custom_price_unit or self.lst_price
            price_udc = 0.0
            log_unit = self.get_uom_po_logistic_unit(supplier_id)
            if uoc_id == supp.log_base_id.id:
                if log_unit == 'base':
                    price_udc = price_unit
                if log_unit == 'unit':
                    price_udc = price_unit * supp.supp_kg_un
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
#
            # if self.lst_price and not price_udc:
            #     raise except_orm(_('Error'), _('The product unit of measure %s is \
            #                      not related with any logistic unit' % uoc_id))
        # import ipdb; ipdb.set_trace()
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
        # import ipdb; ipdb.set_trace()
        res = super(ProductUom, self).name_search(name, args=args,
                                                  operator=operator,
                                                  limit=limit)
        if self._context.get('supp_product_id', False) and \
                self._context.get('supplier_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            # import ipdb; ipdb.set_trace()
            res = recs.name_get()

        return res