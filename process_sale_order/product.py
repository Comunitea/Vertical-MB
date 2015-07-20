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
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round
from openerp.exceptions import except_orm


class product_template(models.Model):
    """
    Adding field minimum unit of sale, and box prices, this fields are Only
    shown in product.product view (Product variants) in order to avoid conflict
    betwen onchanges because of fields list_price of product.template and
    lst_price of product.producr models.
    """
    _inherit = "product.template"

    # @api.model
    # def _get_default_uos(self):
    #     un_uom = self.env['product.uom'].search([('like_type', '=', 'units')])
    #     return un_uom and un_uom.id or False

    # min_unit = fields.Selection([('box', 'Only Boxes'),
    #                             ('unit', 'Only Unit'),
    #                             ('both', 'Both, units and boxes')],
    #                             string='Minimum Sale Unit',
    #                             required=True,
    #                             default='unit',
    #                             help="Selecting both Units and boxes \
    #                             will add functionality to Telesale and \
    #                             Mobile App Sales (Android)")
    box_discount = fields.Float('Box Unit Discount',
                                help="When you sale this product in boxes"
                                "This will be the % discounted over the price"
                                "unit. If a box have 10 units and discount is"
                                "20%, the new box price will be 80 intead of"
                                "100, imaging price unit equals to 1.")
    # Overwrite in order to add 4 decimals
    # uos_coeff = fields.Float('Unit of Measure -> UOS Coeff',
    #                          digits=(16, 4),
    #                          help='Coefficient to convert default Unit of \
    #                          Measure to Unit of Sale\n'' uos = uom * coeff')
    # uos_id = fields.Many2one('product.uom', 'Unit of Sale',
    #                          default=_get_default_uos,
    #                          help='Specify a unit of measure here if invoicing\
    #                          is made in another unit of measure than\
    #                          inventory. Keep empty to use the default unit of \
    #                          measure.')

    # @api.onchange('min_unit')
    # def onchange_min_unit(self):
    #     box_uom = self.env['product.uom'].search([('like_type', '=', 'boxes')])
    #     un_uom = self.env['product.uom'].search([('like_type', '=', 'units')])
    #     res = {}
    #     # if self.min_unit == 'box' or self.min_unit == 'both':
    #     if self.min_unit == 'box':
    #         if not len(box_uom):
    #             res['warning'] = {'title': _('Warning'),
    #                               'message': _('Box unit does not exist.\
    #             You must configured one unit like boxes')}
    #         else:
    #             self.uos_id = box_uom.id

    #     else:  # Units
    #         if not len(un_uom):
    #             res['warning'] = {'title': _('Warning'),
    #                               'message': _('Units unit does not exist.\
    #             You must configured one unit like units')}
    #         else:
    #             self.uos_id = un_uom.id
    #     return res

    # @api.onchange('un_ca')
    # def onchange_un_ca(self):
    #     """ Change uos_coeff acordely to product.un_ca"""
    #     self.uos_coeff = self.un_ca and float_round(1 / self.un_ca, 4) or 0.0

    # @api.onchange('uos_coeff')
    # def onchange_uos_coeff(self):

    #     """ Change un_ca acordely to product.uos_coeff"""
    #     self.un_ca = self.uos_coeff and float_round(1 / self.uos_coeff, 2) \
    #         or 0.0


class product_product(models.Model):

    _inherit = "product.product"

#     @api.onchange('un_ca')
#     def onchange_un_ca(self):
#         """ Change uos_coeff acordely to product.un_ca"""
#         self.uos_coeff = self.un_ca and 1 / self.un_ca or 0.0

#     @api.onchange('uos_coeff')
#     def onchange_uos_coeff(self):
#         """ Change un_ca acordely to product.uos_coeff"""
#         self.un_ca = self.uos_coeff and 1 / self.uos_coeff or 0.0

    @api.model
    def get_sale_unit_ids(self):
        res = []
        if self.base_use_sale and self.log_base_id:
            res.append(self.log_base_id.id)
        if self.unit_use_sale and self.log_unit_id:
            res.append(self.log_unit_id.id)
        if self.box_use_sale and self.log_box_id:
            res.append(self.log_box_id.id)
        return res

    @api.model
    def get_unit_conversions(self, qty_uos, uos_id):
        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0}
        if uos_id == self.log_base_id.id:
            res['base'] = qty_uos
            res['unit'] = float_round(res['base'] / self.kg_un, 2)
            res['box'] = float_round(res['unit'] / self.un_ca, 2)
        elif uos_id == self.log_unit_id.id:
            res['unit'] = qty_uos
            res['box'] = float_round(res['unit'] / self.un_ca, 2)
            res['base'] = float_round(res['unit'] * self.kg_un, 2)
        elif uos_id == self.log_box_id.id:
            res['box'] = qty_uos
            res['unit'] = float_round(res['box'] * self.un_ca, 2)
            res['base'] = float_round(res['unit'] * self.kg_un, 2)
        return res

    @api.model
    def get_uom_logistic_unit(self):
        if self.uom_id.id == self.log_base_id.id:
            return 'base'
        elif self.uom_id.id == self.log_unit_id.id:
            return 'unit'
        elif self.uom_id.id == self.log_box_id.id:
            return 'box'
        else:
            raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_id.name))

    @api.model
    def get_uom_uos_prices(self, uos_id, custom_price_unit=0.0,
                           custom_price_udv=0.0):
        # import ipdb; ipdb.set_trace()
        if custom_price_unit:
            price_unit = custom_price_unit
            price_udv = 0.0
            log_unit = self.get_uom_logistic_unit()
            if uos_id == self.log_base_id.id:
                if log_unit == 'base':
                    price_udv = custom_price_unit
                if log_unit == 'unit':
                    price_udv = price_unit * self.kg_un
                if log_unit == 'box':
                    price_udv = price_unit * self.kg_un * self.un_ca

            elif uos_id == self.log_unit_id.id:
                if log_unit == 'base':
                    price_udv = float_round(custom_price_unit / self.kg_un, 2)
                if log_unit == 'unit':
                    price_udv = price_unit
                if log_unit == 'box':
                    price_udv = price_unit * self.un_ca

            elif uos_id == self.log_box_id.id:
                if log_unit == 'base':
                    price_udv = \
                        float_round(
                            custom_price_unit / (self.kg_un * self.un_ca), 2)
                if log_unit == 'unit':
                    price_udv = float_round(custom_price_unit / self.un_ca, 2)
                if log_unit == 'box':
                    price_udv = price_unit

        else:
            price_udv = custom_price_udv or self.lst_price
            log_unit = self.get_uom_logistic_unit()
            if uos_id == self.log_base_id.id:
                if log_unit == 'base':
                    price_unit = custom_price_udv
                if log_unit == 'unit':
                    price_unit = price_udv * self.kg_un
                if log_unit == 'box':
                    price_unit = price_udv * self.kg_un * self.un_ca
                price_unit = price_unit
            elif uos_id == self.log_unit_id.id:
                if log_unit == 'base':
                    price_unit = float_round(custom_price_unit / self.kg_un, 2)
                if log_unit == 'unit':
                    price_unit = price_udv
                if log_unit == 'box':
                    price_unit = price_udv * self.un_ca
            elif uos_id == self.log_box_id.id:
                if log_unit == 'base':
                    price_unit = \
                        float_round(
                            custom_price_unit / (self.kg_un * self.un_ca), 2)
                if log_unit == 'unit':
                    price_unit = float_round(custom_price_unit / self.un_ca, 2)
                if log_unit == 'box':
                    price_unit = price_udv

            if self.lst_price and not price_udv:
                raise except_orm(_('Error'), _('The product unit of measure %s is \
                                 not related with any logistic unit' % uos_id))
        # import ipdb; ipdb.set_trace()
        return price_unit, price_udv


class ProductUom(models.Model):

    _inherit = 'product.uom'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only allowed products for a partner
            if partner_id is in context."""
        if context is None:
            context = {}
        if context.get('product_id', False):
            t_prod = self.pool.get('product.product')
            prod = t_prod.browse(cr, uid, context['product_id'], context)
            product_udv_ids = prod.get_sale_unit_ids()
            args.append(['id', 'in', product_udv_ids])
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
        if self._context.get('product_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            res = recs.name_get()
        return res
