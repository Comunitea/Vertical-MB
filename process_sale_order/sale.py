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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields as fields2, osv


class sale_order_line2(osv.osv):
    _inherit = "sale.order.line"

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        """
        We must only do sale orders in units or boxes. Same products are only
        in units or only boxes, or maybe we can sale it in boxes and units.
        Field do_onchange is a workarround in order to control product_uos_qty and
        product_uom_qty onchange.
        """
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.choose_unit == 'box':
                unit_of_measure_qty = line.product_uos_qty
            else:
                unit_of_measure_qty = self.product_uom_qty
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, 
                                        unit_of_measure_qty, line.product_id,
                                        line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res

    _columns = {
        'price_subtotal': fields2.function(_amount_line, string='Subtotal',
                                           digits_compute=dp.get_precision
                                           ('Account')),
    }


class sale_order_line(models.Model):
    """
    We must only do sale orders in units or boxes. Same products are only
    in units or only boxes, or maybe we can sale it in boxes and units.
    Field do_onchange is a workarround in order to control product_uos_qty and
    product_uom_qty onchange.
    """
    _inherit = "sale.order.line"

    # @api.one
    # def _amount_line(self, field_name, arg):
    #     """
    #     When we sale in boxes we want to do product_uos_qty * price unit
    #     instead the default product_uom_qty * price_unit
    #     Need call super???
    #     """
    #     import ipdb; ipdb.set_trace()
    #     self.price_subtotal = 0.0
    #     if self.choose_unit == 'box':  # product_uos_qty instead uom
    #         unit_of_measure_qty = self.product_uos_qty
    #     else:  # choose_unit == unit
    #         unit_of_measure_qty = self.product_uom_qty
    #     price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
    #     taxes = self.tax_id.compute_all(price, unit_of_measure_qty,
    #                                     self.product_id,
    #                                     self.order_id.partner_id)
    #     cur = self.order_id.pricelist_id.currency_id
    #     self.price_subtotal = cur.round(taxes['total'])

    min_unit = fields.Selection('Min Unit', related="product_id.min_unit",
                                readonly=True)
    choose_unit = fields.Selection([('unit', 'Unit'),
                                    ('box', 'Box')], 'Selected Unit',
                                   default='unit')
    # price_subtotal = fields.Float('Subtotal', compute=_amount_line,
    #                               digits_compute=dp.get_precision
    #                               ('Product Price'))

    @api.onchange('product_uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the uos of product
        """
        if self.min_unit == 'box' or \
                (self.min_unit == 'both' and self.choose_unit == 'box'):
            self.product_uom_qty = self.product_uos_qty * self.product_id.un_ca
        return

    def product_id_change_with_wh2(self, cr, uid, ids, pricelist, product,
                                   qty=0,
                                   uom=False, qty_uos=0, uos=False, name='',
                                   partner_id=False, lang=False,
                                   update_tax=True,
                                   date_order=False,
                                   packaging=False,
                                   fiscal_position=False, flag=False,
                                   warehouse_id=False,
                                   choose_unit='unit', context=None):
        """
        We overwrite with this name because of midban_depot_stock dependency.
        If we have seted minumum unit of sale, we will call product_id_change
        of price_system_variable module with a 'sale_in_boxes' context in order
        to apply the box_discount field of product to the pricelist price.
        """
        if context is None:
            context = {}
        else:
            context2 = {}
            t_data = self.pool.get('ir.model.data')
            xml_id_name = 'midban_depot_stock.product_uom_box'
            box_id = t_data.xmlid_to_res_id(cr, uid, xml_id_name)
            unit_id = t_data.xmlid_to_res_id(cr, uid,
                                             'product.product_uom_unit')
            prod = self.pool.get("product.product").browse(cr, uid, product)
            min_unit = prod.min_unit
            choose_unit = 'box' if min_unit == 'box' else choose_unit
            if min_unit == 'box' or \
                    (min_unit == 'both' and choose_unit == 'box'):
                for key in context:  # frozen context, we need a no frozen copy
                    context2[key] = context[key]
                context2.update({'sale_in_boxes': True})
            my_context = context2 and context2 or context
            # sup = super(sale_order_line, self)
            fiscal_pos = fiscal_position
            res = self.product_id_change_with_wh(cr, uid, ids, pricelist,
                                                 product, qty=qty, uom=uom,
                                                 qty_uos=qty_uos, uos=uos,
                                                 name=name,
                                                 partner_id=partner_id,
                                                 lang=lang,
                                                 update_tax=update_tax,
                                                 date_order=date_order,
                                                 packaging=packaging,
                                                 fiscal_position=fiscal_pos,
                                                 flag=flag,
                                                 warehouse_id=warehouse_id,
                                                 context=my_context)
            if min_unit == 'unit' or \
                    (min_unit == 'both' and choose_unit == 'unit'):
                res['value']['product_uos_qty'] = qty
                # como uom acaba siendo False en el onchange se calculaa partir
                # del uos y no nos combiene, lo volvemos a setear
                res['value']['product_uom_qty'] = qty
            if min_unit in ['both', 'box']:
                if choose_unit == 'unit':
                    res['value']['product_uom'] = unit_id
                    res['value']['product_uos'] = unit_id
                else:
                    res['value']['product_uom'] = unit_id
                    res['value']['product_uos'] = box_id
                    res['value']['product_uom_qty'] = qty
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
            vals['product_uos_qty'] = qty
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
        because of sometimes they are readonly in the view and the onchange
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
        vals['type'] = 'pff'  # Set any value to avoid the onchange in super
        res = super(sale_order_line, self).create(vals)

        return res


class sale_order(models.Model):
    """
    """
    _inherit = "sale.order"

    def _amount_line_tax(self, cr, uid, line, context=None):
        """
        Overwrite to get a correct amount_tax value when we sale in boxes with
        the box discount value applied.
        """
        t_tax = self.pool.get('account.tax')
        val = super(sale_order, self)._amount_line_tax(cr, uid, line,
                                                       context=context)
        if line.choose_unit == 'box':
            val = 0.0
            desc = (1 - (line.discount or 0.0) / 100.0)
            for c in t_tax.compute_all(cr, uid, line.tax_id,
                                       line.price_unit * desc,
                                       line.product_uos_qty, line.product_id,
                                       line.order_id.partner_id)['taxes']:
                val += c.get('amount', 0.0)
        return val
