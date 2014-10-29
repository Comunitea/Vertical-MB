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


class sale_order_line(models.Model):
    """
    We must only do sale orders in units or boxes. Same products are only
    in units or only boxes, or maybe we can sale it in boxes and units.
    Field do_onchange is a workarround in order to control product_uos_qty and
    product_uom_qty onchange.
    """
    _inherit = "sale.order.line"

    min_unit = fields.Selection('Min Unit', related="product_id.min_unit",
                                readonly=True)
    choose_unit = fields.Selection([('unit', 'Unit'),
                                    ('box', 'Box')], 'Selected Unit',
                                   default='unit')

    @api.onchange('product_uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the uos of product
        """
        if self.min_unit == 'box' or \
                (self.min_unit == 'both' and self.choose_unit == 'box'):
            self.product_uom_qty = self.product_id.uos_coeff != 0 and \
                self.product_uos_qty / self.product_id.uos_coeff or \
                self.product_uom_qty
        return

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='',
                          partner_id=False, lang=False, update_tax=True,
                          date_order=False, packaging=False,
                          fiscal_position=False, flag=False,
                          choose_unit='unit', context=None):
        """
        If we have seted minumum unit of sale, we will call product_id_change
        of price_system_variable module with a 'sale_in_boxes' context in order
        to apply the box_discount field of product to the pricelist price.
        """
        if context is None:
            context = {}
        else:
            t_data = self.pool.get('ir.model.data')
            xml_id_name = 'midban_depot_stock.product_uom_box'
            box_id = t_data.xmlid_to_res_id(cr, uid, xml_id_name)
            unit_id = t_data.xmlid_to_res_id(cr, uid,
                                             'product.product_uom_unit')
            prod = self.pool.get("product.product").browse(cr, uid, product)
            min_unit = prod.min_unit
            if min_unit == 'box' or \
                    (min_unit == 'both' and choose_unit == 'box'):

                context = {'sale_in_boxes': True}
            sup = super(sale_order_line, self)
            res = sup.product_id_change(cr, uid, ids, pricelist, product,
                                        qty=qty, uom=uom, qty_uos=qty_uos,
                                        uos=uos, name=name,
                                        partner_id=partner_id,
                                        lang=lang, update_tax=update_tax,
                                        date_order=date_order,
                                        packaging=packaging,
                                        fiscal_position=fiscal_position,
                                        flag=flag, context=context)
            if min_unit == 'unit' or \
                    (min_unit == 'both' and choose_unit == 'unit'):
                res['value']['product_uos_qty'] = qty
            if min_unit == 'both':
                if choose_unit == 'unit':
                    res['value']['product_uom'] = unit_id
                    res['value']['product_uos'] = unit_id
                else:
                    res['value']['product_uom'] = unit_id
                    res['value']['product_uos'] = box_id
        return res

    @api.one
    def write(self, vals):
        """
        Overwrite to recalculate the product_uom_qty and product_uos_qty
        because of sometimes thei are readonly in the view and the onchange
        value is not in the vals dict
        """
        t_data = self.env['ir.model.data']
        if vals.get('product_id', False):
            prod = self.env['product.product'].browse(vals['product_id'])
        else:
            prod = self.product_id
        xml_id_name = 'midban_depot_stock.product_uom_box'
        box_id = t_data.xmlid_to_res_id(xml_id_name)
        unit_id = t_data.xmlid_to_res_id('product.product_uom_unit')
        min_unit = vals.get('min_unit', False) and vals['min_unit'] or \
            prod.min_unit
        choose = vals.get('choose_unit', False) and vals['choose_unit'] \
            or self.choose_unit
        if min_unit == 'unit' or (min_unit == 'both' and choose == 'unit'):
            qty = vals.get('product_uom_qty', 0.0) and \
                vals['product_uom_qty'] or self.product_uom_qty
            vals['product_uos_qty'] = vals.get('product_uom_qty', 0.0)
            vals['product_uos'] = unit_id
            vals['product_uom'] = unit_id
            vals['choose_unit'] = 'unit'
        elif min_unit == 'box' or (min_unit == 'both' and choose == 'box'):
            uos_coeff = prod.uos_coeff
            uos_qty = vals.get('product_uos_qty', 0.0) and \
                vals['product_uos_qty'] or self.product_uos_qty
            qty = uos_coeff and uos_qty / uos_coeff or 0.0
            vals['product_uom_qty'] = qty
            vals['product_uos'] = box_id
            vals['product_uom'] = unit_id
            vals['choose_unit'] = 'box'
        res = super(sale_order_line, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        """
        Overwrite to recalculate the product_uom_qty and product_uos_qty
        because of sometimes thei are readonly in the view and the onchange
        value is not in the vals dict
        """
        t_data = self.env['ir.model.data']
        if vals.get('product_id', False):
            prod = self.env['product.product'].browse(vals['product_id'])
            xml_id_name = 'midban_depot_stock.product_uom_box'
            box_id = t_data.xmlid_to_res_id(xml_id_name)
            unit_id = t_data.xmlid_to_res_id('product.product_uom_unit')
            min_unit = vals.get('min_unit', False) and vals['min_unit'] or \
                prod.min_unit
            choose2 = min_unit in ['unit', 'both'] and 'unit' or 'box'
            choose = vals.get('choose_unit', False) and vals['choose_unit'] \
                or choose2
            if min_unit == 'unit' or (min_unit == 'both' and choose == 'unit'):
                qty = vals.get('product_uom_qty', 0.0)
                vals['product_uos_qty'] = vals.get('product_uom_qty', 0.0)
                vals['product_uos'] = unit_id
                vals['product_uom'] = unit_id
                vals['choose_unit'] = 'unit'
            elif min_unit == 'box' or (min_unit == 'both' and choose == 'box'):
                uos_coeff = prod.uos_coeff
                uos_qty = vals.get('product_uos_qty', 0.0)
                qty = uos_coeff and uos_qty / uos_coeff or 0.0
                vals['product_uom_qty'] = qty
                vals['product_uos'] = box_id
                vals['product_uom'] = unit_id
                vals['choose_unit'] = 'box'
        res = super(sale_order_line, self).create(vals)

        return res
