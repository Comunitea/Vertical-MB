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
from openerp import models, fields


class product_template(models.Model):
    """
    Adding field minimum unit of sale, and box prices, this fields are Only
    shown in product.product view (Product variants) in order to avoid conflict
    betwen onchanges because of fields list_price of product.template and
    lst_price of product.producr models.
    """
    _inherit = "product.template"

    min_unit = fields.Selection([('box', 'Only Boxes'),
                                ('unit', 'Only Unit'),
                                ('both', 'Both, units and boxes')],
                                string='Minimum Sale Unit',
                                required=True,
                                default='both')
    price_box_unit = fields.Float('Unit price box')
    box_price = fields.Float('Box Price')
    box_discount = fields.Float('Box Discount')
    integer = fields.Integer('Integer', readonly=True)

# @api.onchange('price_box_unit')
    # def change_box_price_and_discount(self):
    #     import ipdb; ipdb.set_trace()
    #     if self.list_price:
    #         self.box_price = self.price_box_unit * self.un_ca
    #         diff = self.list_price - self.price_box_unit
    #         self.box_discount = (diff / self.list_price) * 100.0

    # @api.onchange('box_price')
    # def change_price_box_unit_and_discount(self):
    #     import ipdb; ipdb.set_trace()
    #     if self.list_price:
    #         self.price_box_unit = self.un_ca and \
    #             self.price_box_unit / self.un_ca or 0.0
    #         diff = self.list_price - self.price_box_unit
    #         self.box_discount = (diff / self.list_price) * 100.0

    # @api.onchange('box_discount')
    # def change_unit_and_box_price(self):
    #     import ipdb; ipdb.set_trace()
    #     if self.list_price
    #         unit_price = self.list_price * (1 - self.box_discount / 100.0)
    #         self.price_box_unit = unit_price
    #         self.box_price = self.price_box_unit * self.un_ca

    # def onchange_box_prices_fields(self, cr, uid, ids, list_price,
    #                                price_box_unit, box_price, box_discount,
    #                                flag, integer):
        #  """
        # Integer is used like workarround to avoid change fields more than one
        # time. a change in one field triggers two more calls, we need to avoid
        # the changes the second and third time.
        # Due to odoo takes the previous change in a field if the last value
        # is the same to the begining we need to use a integer to count like
        # this:
        # first with integer=0 ---> 1,2,3(first group  3 calls)  then
        # integer=3 --->4,5,0 (second group of 3 calls), etc...
        # """
    #     res = {}
    #     prod = self.browse(cr, uid, ids[0])
    #     if integer in [0, 3]:
    #         if flag == "price_box_unit":
    #             diff = list_price - price_box_unit
    #             res['value'] = {
    #                 'box_price': price_box_unit * prod.un_ca,
    #                 'box_discount': (diff / list_price) * 100.0
    #             }

    #         elif flag == "box_price":
    #             unit_price = prod.un_ca and box_price / prod.un_ca or 0.0
    #             diff = list_price - unit_price
    #             res['value'] = {
    #                 'price_box_unit': unit_price,
    #                 'box_discount': (diff / list_price) * 100.0
    #             }
    #         elif flag == "box_discount":
    #             unit_price = list_price * (1 - box_discount / 100.0)
    #             res['value'] = {
    #                 'price_box_unit': unit_price,
    #                 'box_price': unit_price * prod.un_ca
    #             }
    #         res['value']['integer'] = (integer == 0) and 1 or 4

    #     elif integer in [1, 4]:
    #         res = {'value': {'integer': (integer == 1) and 2 or 5}}

    #     elif integer in [2, 5]:
    #         res = {'value': {'integer': (integer == 2) and 3 or 0}}
    #     return res


class product_product(models.Model):
    """
    Adding field minimum unit of sale.
    """
    _inherit = "product.product"

    def onchange_box_prices_fields2(self, cr, uid, ids, lst_price,
                                    price_box_unit, box_price, box_discount,
                                    flag, integer):
        """
        Integer is used like workarround to avoid change fields more than one
        time. a change in one field triggers two more calls, we need to avoid
        the changes the second and third time.
        Due to odoo takes the previous change in a field if the last value
        is the same to the begining we need to use a integer to count like
        this:
        first with integer=0 ---> 1,2,3(first group 3 calls) then
        integer=3 --->4,5,0 (second group of 3 calls), etc...
        """
        # import ipdb; ipdb.set_trace()
        res = {}
        prod = self.browse(cr, uid, ids[0])
        if integer < 0:
            res = {'value': {'integer': integer + 1}}
        elif integer in [0, 3]:
            if flag == "price_box_unit":
                diff = lst_price - price_box_unit
                res['value'] = {
                    'box_price': price_box_unit * prod.un_ca,
                    'box_discount': (diff / lst_price) * 100.0
                }

            elif flag == "box_price":
                unit_price = prod.un_ca and box_price / prod.un_ca or 0.0
                diff = lst_price - unit_price
                res['value'] = {
                    'price_box_unit': unit_price,
                    'box_discount': (diff / lst_price) * 100.0
                }
            elif flag in ["box_discount", "lst_price"]:
                unit_price = lst_price * (1 - box_discount / 100.0)
                res['value'] = {
                    'price_box_unit': unit_price,
                    'box_price': unit_price * prod.un_ca
                }
            res['value']['integer'] = (integer == 0) and 1 or 4

        elif integer in [1, 4]:
            res = {'value': {'integer': (integer == 1) and 2 or 5}}

        elif integer in [2, 5]:
            res = {'value': {'integer': (integer == 2) and 3 or 0}}
        return res
