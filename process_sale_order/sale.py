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


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    price_udv = fields.Float('Price UdV',
                             digits_compute=dp.get_precision('Product Price'))
    do_onchange = fields.Boolean('Do onchange', default=True)

    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product,
                                  qty=0, uom=False, qty_uos=0, uos=False,
                                  name='', partner_id=False, lang=False,
                                  update_tax=True,
                                  date_order=False,
                                  packaging=False,
                                  fiscal_position=False, flag=False,
                                  warehouse_id=False, context=None):
        """
        We overwrite with this name because of midban_depot_stock dependency.
        Is defined in sale_stock module
        """
        if context is None:
            context = {}
        fpos = fiscal_position
        sup = super(sale_order_line, self)
        res = sup.product_id_change_with_wh(cr, uid, ids, pricelist,
                                            product, qty=qty, uom=uom,
                                            qty_uos=qty_uos, uos=uos,
                                            name=name,
                                            partner_id=partner_id,
                                            lang=lang,
                                            update_tax=update_tax,
                                            date_order=date_order,
                                            packaging=packaging,
                                            fiscal_position=fpos,
                                            flag=flag,
                                            warehouse_id=warehouse_id,
                                            context=context)
        if not product:
            return res
        prod_obj = self.pool.get('product.product').browse(cr, uid,
                                                           product,
                                                           context=context)
        product_udv_ids = prod_obj.get_sale_unit_ids()
        # uom_domain = [('id', 'in', product_udv_ids)]
        # res['domain'] = {'product_uos': uom_domain}
        res['value']['product_uos'] = \
            product_udv_ids and product_udv_ids[0] or False
        res['value']['product_uom'] = prod_obj.uom_id.id
        res['value']['product_uos_qty'] = 1.0
        return res

    @api.onchange('product_uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the product_uom_qty
        """
        # import ipdb; ipdb.set_trace()
        product = self.product_id
        if product:
            if self.do_onchange:
                qty = self.product_uos_qty
                uos_id = self.product_uos.id

                conv = product.get_unit_conversions(qty, uos_id)
                # base, unit, or box
                log_unit = product.get_uom_logistic_unit()
                self.product_uom_qty = conv[log_unit]
            else:
                self.do_onchange = True

    @api.onchange('product_uos')
    def product_uos_onchange(self):
        """
        We change the product_uom_qty
        """
        # import ipdb; ipdb.set_trace()
        product = self.product_id
        if product:
            # Change Uom Qty
            uos_id = self.product_uos.id
            uos_qty = self.product_uos_qty
            conv = product.get_unit_conversions(uos_qty, uos_id)
            log_unit = product.get_uom_logistic_unit()
            self.product_uom_qty = conv[log_unit]

            # Calculate prices
            uom_pu, uos_pu = product.get_uom_uos_prices(uos_id,
                                                        custom_price_unit=self.
                                                        price_unit)
            self.do_onchange = False
            # self.price_unit = uom_pu
            self.price_udv = uos_pu
            self.do_onchange = False  # Avoid onchange_price_udv

    @api.model
    def write(self, vals):
        """
        Overwrite to recalculate the product_uom_qty and product_uom
        because they are readonly in the view and the onchange
        value is not in the vals dict
        """
        if vals.get('product_id', False):
            prod = self.env['product.product'].browse(vals['product_id'])
        else:
            prod = self.product_id
        uos_qty = vals.get('product_uos_qty', False) and \
            vals['product_uos_qty'] or self.product_uos_qty
        uos_id = vals.get('product_uos', False) and \
            vals['product_uos'] or self.product_uos.id
        conv = prod.get_unit_conversions(uos_qty, uos_id)
        log_unit = prod.get_uom_logistic_unit()  # base, unit, or box
        vals['product_uom_qty'] = conv[log_unit]
        vals['product_uom'] = prod.uom_id.id
        res = super(sale_order_line, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        """
        Overwrite to recalculate the product_uom_qty and product_uos_qty
        because of sometimes they are readonly in the view and the onchange
        value is not in the vals dict
        """
        if vals.get('product_id', False):
            prod = self.env['product.product'].browse(vals['product_id'])
            uos_qty = vals.get('product_uos_qty', False) and \
                vals['product_uos_qty'] or 0.0
            uos_id = vals.get('product_uos', False) and \
                vals['product_uos'] or False

            conv = prod.get_unit_conversions(uos_qty, uos_id)
            log_unit = prod.get_uom_logistic_unit()  # base, unit, or box
            vals['product_uom_qty'] = conv[log_unit]
            vals['product_uom'] = prod.uom_id.id
        res = super(sale_order_line, self).create(vals)

        return res

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        """
        We change the product_uom_qty
        """
        # import ipdb; ipdb.set_trace()
        product = self.product_id
        if product:
            if self.do_onchange:
                uos = self.product_uos
                uos_id = uos.id
                uom_pu, uos_pu = \
                    product.get_uom_uos_prices(uos_id,
                                               custom_price_unit=self.
                                               price_unit)
                self.do_onchange = False
                self.price_udv = uos_pu
            else:
                self.do_onchange = True

    @api.onchange('price_udv')
    def price_udv_onchange(self):
        """
        We change the product_uom_qty
        """
        # import ipdb; ipdb.set_trace()
        product = self.product_id
        if product:
            if self.do_onchange:
                uos_id = self.product_uos.id
                # Calculate prices
                uom_pu, uos_pu = \
                    product.get_uom_uos_prices(uos_id,
                                               custom_price_udv=self.price_udv)
                self.do_onchange = False
                self.price_unit = uom_pu
            else:
                self.do_onchange = True

    # @api.multi
    # def onchange_price_unit(self, product_id, price_unit, pricelist_id,
    #                         product_uos):
    #     """
    #     Raises a warning if price unit lower than minimum price defined in
    #     change_product_pvp for the current product.
    #     """
    #     import ipdb; ipdb.set_trace()
    #     res = super(sale_order_line, self).onchange_price_unit(product_id,
    #                                                            price_unit,
    #                                                            pricelist_id,
    #                                                            product_uos)

    #     t_product = self.env["product.product"]
    #     # t_pricelist = self.env["product.pricelist"]
    #     t_uom = self.env["product.uom"]
    #     if product_id and pricelist_id and product_uos:
    #         if self.do_onchange:
    #             product = t_product.browse(product_id)
    #             uos = t_uom.browse(product_uos)
    #             uos_id = uos.id
    #             uom_pu, uos_pu = \
    #                 product.get_uom_uos_prices(uos_id,
    #                                            custom_price_unit=price_unit)
    #             self.do_onchange = False
    #             res['value']['price_udv'] = uos_pu
    #             res['value']['price_unit'] = price_unit
    #         else:
    #             self.do_onchange = True
        # return res
