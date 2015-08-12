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
# from openerp.exceptions import except_orm
from openerp.tools.translate import _


class purchase_order_line(models.Model):

    _inherit = 'purchase.order.line'

    product_uoc_qty = fields.Float('Quantity (UdC)',
                                   digits_compute=dp.
                                   get_precision('Product Unit of Measure'))
    product_uoc = fields.Many2one('product.uom', 'Unit of Buy')
    price_udc = fields.Float('Price UdC',
                             digits_compute=dp.get_precision('Product Price'))
    do_onchange = fields.Boolean('Do onchange', default=True)

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty,
                            uom_id, partner_id, date_order=False,
                            fiscal_position_id=False, date_planned=False,
                            name=False, price_unit=False, state='draft',
                            context=None):
        """
        """
        if context is None:
            context = {}
        sup = super(purchase_order_line, self)
        res = sup.onchange_product_id(cr, uid, ids, pricelist_id, product_id,
                                      qty, uom_id, partner_id,
                                      context=context,
                                      date_order=date_order,
                                      fiscal_position_id=fiscal_position_id,
                                      date_planned=date_planned,
                                      name=name,
                                      price_unit=price_unit,
                                      state=state)
        if not product_id:
            return res

        # Get description of line
        t_product = self.pool.get('product.product')
        prod_obj = t_product.browse(cr, uid, product_id)
        dumy_id, name = prod_obj.name_get()[0]
        if prod_obj.description_purchase:
            name += '\n' + prod_obj.description_purchase
        res['value'].update({'name': name})

        if partner_id:
            t_partner = self.pool.get('res.partner')
            part_obj = t_partner.browse(cr, uid, partner_id)

            # Check partner_id in product's suppliers list, if founded
            # all logistic information is setted, because it has been checked
            # in midban product module when logistic validated
            supplier_ids = [x.name.id for x in prod_obj.seller_ids]
            if partner_id not in supplier_ids:
                res['value']['product_id'] = False
                res['value']['name'] = ''
                res['value']['date_planned'] = False
                res['value']['account_analytic_id'] = False
                res['value']['product_qty'] = 0.0
                res['value']['product_uom'] = False
                res['value']['price_unit'] = 0.0
                res['value']['taxes_id'] = False
                res['value']['product_uoc'] = False
                res['value']['product_uoc_qty'] = 0.0
                res['value']['price_udc'] = 0.0

                res['warning'] = {'title': _('Warning!'),
                                  'message': _('Supplier %s not founded in \
                                                 product suppliers \
                                                 list') % part_obj.name
                                  }
            else:
                product_udc_ids = prod_obj.get_purchase_unit_ids(partner_id)
                res['value']['product_uoc'] = \
                    product_udc_ids and product_udc_ids[0] or False
                res['value']['product_uoc_qty'] = 1.0
        return res

    @api.onchange('product_uoc_qty')
    def product_uoc_qty_onchange(self):
        """
        We change the product_uom_qty
        """

        product = self.product_id
        if product:
            if self.do_onchange:
                supplier_id = self.order_id.partner_id.id
                qty = self.product_uoc_qty
                uoc_id = self.product_uoc.id

                conv = product.get_purchase_unit_conversions(qty, uoc_id,supplier_id)
                # base, unit, or box
                import pdb; pdb.set_trace()
                log_unit = product.get_uom_po_logistic_unit(supplier_id)
                self.product_qty = conv[log_unit]
            else:
                self.do_onchange = True

    @api.onchange('product_uoc')
    def product_uoc_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            supplier_id = self.order_id.partner_id.id
            # Change Uom Qty
            uoc_id = self.product_uoc.id
            uoc_qty = self.product_uoc_qty
            conv = product.get_purchase_unit_conversions(uoc_qty, uoc_id,
                                                         supplier_id)
            log_unit = product.get_uom_po_logistic_unit(supplier_id)
            self.product_qty = conv[log_unit]

            # Calculate prices
            uom_pu, uoc_pu = product.get_uom_uoc_prices_purchases(uoc_id, supplier_id,
                                                        )
            # Avoid trigger onchange_price_udv, because is already calculed
            if uoc_pu != self.price_udc:
                self.do_onchange = False
            self.price_unit = uom_pu
            self.price_udc = uoc_pu

    @api.multi
    def write(self, vals):
        """
        Overwrite to recalculate the product_qty and product_uom
        because they are readonly in the view and the onchange
        value is not in the vals dict
        """
        for po_line in self:
            if vals.get('product_id', False):
                prod = self.env['product.product'].browse(vals['product_id'])
            else:
                prod = po_line.product_id

            supplier_id = po_line.order_id.partner_id.id
            uoc_qty = vals.get('product_uoc_qty', False) and \
                vals['product_uoc_qty'] or po_line.product_uoc_qty
            uoc_id = vals.get('product_uoc', False) and \
                vals['product_uoc'] or po_line.product_uoc.id
            conv = prod.get_purchase_unit_conversions(uoc_qty, uoc_id, supplier_id)
            log_unit = prod.get_uom_po_logistic_unit(supplier_id)  # base, unit, box
            vals['product_qty'] = conv[log_unit]
            vals['product_uom'] = prod.uom_id.id  # Deafult stock unit?
            res = super(purchase_order_line, po_line).write(vals)
        return res

    @api.model
    def create(self, vals):
        """
        Overwrite to recalculate the product_qty and product_uom
        because of sometimes they are readonly in the view and the onchange
        value is not in the vals dict
        """
        if vals.get('product_id', False) and vals.get('order_id', False):
            purchase_id = self.env['purchase.order'].browse(vals['order_id'])
            supplier_id = purchase_id.partner_id.id
            prod = self.env['product.product'].browse(vals['product_id'])
            uoc_qty = vals.get('product_uoc_qty', False) and \
                vals['product_uoc_qty'] or 0.0
            uoc_id = vals.get('product_uoc', False) and \
                vals['product_uoc'] or False

            conv = prod.get_purchase_unit_conversions(uoc_qty, uoc_id,
                                                      supplier_id)
            log_unit = prod.get_uom_po_logistic_unit(supplier_id)  # base, unit, or box
            vals['product_qty'] = conv[log_unit]
            vals['product_uom'] = prod.uom_id.id  # Deafult stock unit?
        res = super(purchase_order_line, self).create(vals)

        return res

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        supplier_id = self.order_id.partner_id.id
        if product:
            if self.do_onchange:
                uoc = self.product_uoc
                uoc_id = uoc.id
                uom_pu, uoc_pu = \
                    product.get_uom_uoc_prices_purchases(uoc_id, supplier_id,
                                               custom_price_unit=self.
                                               price_unit)
                # Avoid trigger onchange_price_udv, because is already calculed
                if uoc_pu != self.price_udc:
                    self.do_onchange = False
                self.price_udc = uoc_pu
            else:
                self.do_onchange = True

    @api.onchange('price_udc')
    def price_udc_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        supplier_id = self.order_id.partner_id.id
        if product:
            if self.do_onchange:
                uoc_id = self.product_uoc.id
                # Calculate prices
                uom_pu, uoc_pu = \
                    product.get_uom_uoc_prices_purchases(uoc_id, supplier_id,
                                               custom_price_udc=self.price_udc)
                # Avoid trigger onchange_price_unit,lready calculed
                if uom_pu != self.price_unit:
                    self.do_onchange = False
                self.price_unit = uom_pu
            else:
                self.do_onchange = True
