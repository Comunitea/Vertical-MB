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
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import time
from openerp.tools.translate import _


class sale_order_line(osv.osv):
    """ Overwrited to add a column 'to_update' that mark line as to be updated
        when product satisfaces a pricelist rule based on Variable pricelist.
    """
    _inherit = 'sale.order.line'
    _columns = {
        'to_update': fields.boolean('To be updated'),
        'change_id': fields.many2one('change.variable.pricelist', 'Change')
    }
    _defaults = {
        'to_update': False
    }

    def write(self, cr, uid, ids, vals, context=None):
        """
        Overwrite to raise a exception if price unit is less than min price.
        """
        t_pricelist = self.pool.get("product.pricelist")
        if 'price_unit' in vals:
            for line in self.browse(cr, uid, ids, context):
                if line.product_id.product_class in ['fresh', 'no_class']:
                    continue
                pricelist_id = line.order_id.pricelist_id.id
                min_price = t_pricelist._get_product_pvp(cr, uid,
                                                         line.product_id.id,
                                                         pricelist_id)[1]
                if vals['price_unit'] < min_price:
                    msg = "Product {} has a price unit ({}) less than his \
                           minimum price ({}) for current purchase pricelist" \
                           .format(line.product_id.name, vals['price_unit'],
                                   min_price)
                    raise osv.except_osv(_('Error!'), msg)

        res = super(sale_order_line, self).write(cr, uid, ids, vals, context)
        return res

# def create(self, cr, uid, vals, context=None):
#     """
#     Overwrite to raise a exception if price unit is less than min price.
#     """
#     t_pricelist = self.pool.get("product.pricelist")
#     t_product = self.pool.get("product.product")
#     t_sale = self.pool.get("sale.order")
#     if 'price_unit' in vals and 'product_id' in vals:
#         product = t_product.browse(cr, uid, vals['product_id'], context)
#         if product.product_class not in ['fresh', 'no_class']:
#             order = t_sale.browse(cr, uid, vals['order_id'], context)
#             pricelist_id = order.pricelist_id.id
#             min_price = t_pricelist._get_product_pvp(cr, uid,
#                                                      product.id,
#                                                      pricelist_id)[1]
#             if vals['price_unit'] < min_price:
#                     msg = "Product {} has a price unit ({}) less than his \
#                            minimum price ({}) for current purchase \
#                            pricelist".format(product.name,
#                                              vals['price_unit'], min_price)
#                     raise osv.except_osv(_('Error!'), msg)

#     res = super(sale_order_line, self).create(cr, uid, vals, context)
#     return res

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='',
                          partner_id=False, lang=False, update_tax=True,
                          date_order=False, packaging=False,
                          fiscal_position=False, flag=False, context=None):
        """
        We search the appropiate pricelist rule (product.pricelist.item)
        an if it is based on variable pricelit we mark the write field
        '2beupdeted of the current line.
        If rule is based on change product pvp it get the price searching in
        that model. Also search for specific_customer_prices. If someone was
        found return as price_unit the especific price
        """
        sup = super(sale_order_line, self)
        res = sup.product_id_change(cr, uid, ids, pricelist, product,
                                    qty=0, uom=uom, qty_uos=qty_uos, uos=uos,
                                    name=name, partner_id=partner_id,
                                    lang=lang, update_tax=update_tax,
                                    date_order=date_order,
                                    packaging=packaging,
                                    fiscal_position=fiscal_position,
                                    flag=flag, context=context)
        if not product:
            return res  # In super returns dict with seted default values
        t_p_list = self.pool.get('product.pricelist')
        t_product = self.pool.get('product.product')
        t_partner = self.pool.get('res.partner')
        t_item = self.pool.get('product.pricelist.item')
        # Calcuate required args to cal price_get_multi in order to know
        # the associated pricelist rule for the product
        if pricelist:
            if partner_id:
                lang = t_partner.browse(cr, uid, partner_id).lang
            context_partner = {'lang': lang, 'partner_id': partner_id}
            product_obj = t_product.browse(cr, uid, product,
                                           context=context_partner)
            # uom = a res_uom o algo asi???
            if not date_order:
                date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            context2 = {
                'uom': uom or product_obj.uom_id.id,
                'date': date_order
            }
            # price_get_multi return a dict with the property pricelit rule
            # for the product
            prod_obj = t_product.browse(cr, uid, product, context)
            res_multi = t_p_list.price_get_multi(cr, uid,
                                                 pricelist_ids=[pricelist],
                                                 products_by_qty_by_partner=
                                                 [(prod_obj, qty or 1.0,
                                                  partner_id)],
                                                 context=context2)
            if type(res_multi[product]) == dict:
                item_id = res_multi[product].get('item_id', False)
            else:
                item_id = False
            res['value'].update({'to_update': False})
            if item_id:
                item = t_item.browse(cr, uid, item_id)
                # if item is based on variable pricelist mark line as 2beupdate
                if item.base == -3:
                    res['value'].update({'to_update': True})
                # if rule(item) is based on change.product.pvp
                elif item.base == -5:
                    p_plist = self.pool.get('product.pricelist')
                    uom_or = res['value'].get('product_uom')
                    #SEARCH FOR SPECIFIC PRICE IF EXISTS
                    t_specific = self.pool.get("specific.pvp.line")
                    domain = [('specific_id.partner_id', '=', partner_id),
                              ('specific_id.state', '=', 'updated'),
                              ('product_id', '=', product),
                              ('date_start', '<=', time.strftime('%Y-%m-%d')),
                              ('date_end', '>=', time.strftime('%Y-%m-%d'))]
                    spc_ids = t_specific.search(cr, uid, domain, limit=1,
                                                order="id desc")
                    if spc_ids:
                        spc_line = t_specific.browse(cr, uid, spc_ids[0])
                        price = spc_line.specific_pvp
                        res['value']['price_unit'] = price
                        return res
                    #SEARCH FOR CHANGE PRODUCT PVP
                    price = p_plist.price_get(cr, uid, [pricelist],
                                              product, qty or 1.0, partner_id,
                                              {'uom': uom or uom_or,
                                               'date': date_order})[pricelist]
                    if price == "warn":
                        price = 0.0
                        spa = u"No existe Cambio PVP de producto adecuado \
                                para el producto y la tarifa de venta \
                                actuales. Quizás el modelo no está \
                                actualizado o la fecha no está en el rango."
                        # 'message': _('There is no change \
                                          #  product pvp rule for \
                                          #   this product.')
                        res['warning'] = {'title': _('Warning!'),
                                          'message': spa
                                          }
                    res['value']['price_unit'] = price
        return res

    def onchange_price_unit(self, cr, uid, ids, product_id, price_unit,
                            pricelist_id, context=None):
        """
        Raises a warning if price unit lower than minimum price defined in
        change_product_pvp for the current product.
        """
        if context is None:
            context = {}
        res = {'value': {}}
        t_product = self.pool.get("product.product")
        t_pricelist = self.pool.get("product.pricelist")
        if product_id and pricelist_id:
            product = t_product.browse(cr, uid, product_id, context)
            if product.product_class in ['dry', 'frozen', 'chilled']:
                min_price = t_pricelist._get_product_pvp(cr, uid, product_id,
                                                         pricelist_id)[1]
                if price_unit < min_price:
                    # msg = "Product {} has a price unit ({}) less than his \
                    #      minimum price ({}) for current purchase pricelist" \
                    #         .format(product.name, price_unit, min_price)
                    spa = "El producto {} tiene un precio unitario ({}) menor \
                    que su precio mínimo ({}) para la tarifa de venta actual. \
                    " \
                    .format(product.name, price_unit, min_price)
                    res['warning'] = {'title': _('Warning!'),
                                      'message': spa}
                    res['value']['price_unit'] = price_unit
        return res
