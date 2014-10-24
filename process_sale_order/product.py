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
from openerp import models, fields, api, _


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
    box_discount = fields.Float('Box Unit Discount')

    @api.onchange('min_unit')
    def onchange_min_unit(self):
        box_uom = self.env['product.uom'].search([('like_type', '=', 'boxes')])
        un_uom = self.env['product.uom'].search([('like_type', '=', 'units')])
        res = {}
        if self.min_unit == 'box' or self.min_unit == 'both':
            if not len(box_uom):
                res['warning'] = {'title': _('Warning'),
                                  'message': _('Box unit does not exist.\
                You must configured one unit like boxes')}
            else:
                self.uos_id = box_uom.id

        else:  # Units
            if not len(un_uom):
                res['warning'] = {'title': _('Warning'),
                                  'message': _('Box unit does not exist.\
                You must configured one unit like units')}
            else:
                self.uos_id = un_uom.id
        return res

    @api.onchange('un_ca')
    def onchange_un_ca(self):
        """ Change uos_coeff acordely to product.un_ca"""
        self.uos_coeff = self.un_ca and 1 / self.un_ca or 0.0


# class product_template(models.Model):

#     _inherit = "product.product"

#     @api.onchange('un_ca')
#     def onchange_un_ca(self):
#         """ Change uos_coeff acordely to product.un_ca"""
#         self.uos_coeff = self.un_ca and 1 / self.un_ca or 0.0