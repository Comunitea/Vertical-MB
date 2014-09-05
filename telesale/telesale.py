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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class sale_order_line(osv.osv):
    """ Overwrited to add a column pvp_ref corresponding to same field in
        orderline backbone model in the client part.
        this field saves the value of product pvp line in order to change
        discount property in the ProductInfoWidget.
    """
    _inherit = 'sale.order.line'

    def _get_current_pvp(self, cr, uid, ids, field_name, args,
                         context=None):
        """
        Calcs function field current_pvp in order to get the line's price unit
        back and send it to telesale front end.
        """
        res = {}
        t_priclist = self.pool.get("product.pricelist")
        for line in self.browse(cr, uid, ids, context):
            pricelist_id = line.order_id.pricelist_id.id
            result = t_priclist._get_product_pvp(cr, uid, line.product_id.id,
                                                 pricelist_id)
            res[line.id] = result[0] or 0.0
        return res

    _columns = {
        'pvp_ref': fields.float('PVP ref',
                                digits_compute=
                                dp.get_precision('Product Price'),
                                readonly=True),
        'last_price_fresh': fields.float('Last Price Fresh',
                                         digits_compute=
                                         dp.get_precision('Product Price'),
                                         readonly=True),
        'current_pvp': fields.function(_get_current_pvp, type="float",
                                       string="Current PVP",
                                       readonly=True),
    }

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='',
                          partner_id=False, lang=False, update_tax=True,
                          date_order=False, packaging=False,
                          fiscal_position=False, flag=False, context=None):
        """
        Overwrite in order to get the last sale preice to calculate a
        aproximate price of fresh products in telesale
        """
        if context is None:
            context = {}
        sup = super(sale_order_line, self)
        t_product = self.pool.get('product.product')
        res = sup.product_id_change(cr, uid, ids, pricelist, product,
                                    qty=0, uom=uom, qty_uos=qty_uos, uos=uos,
                                    name=name, partner_id=partner_id,
                                    lang=lang, update_tax=update_tax,
                                    date_order=date_order,
                                    packaging=packaging,
                                    fiscal_position=fiscal_position,
                                    flag=flag, context=context)
        res['value']['last_price_fresh'] = 0.0
        if product and pricelist:
            prod_obj = t_product.browse(cr, uid, product, context)
            if prod_obj.product_class == "fresh":
                domain = [('product_id', '=', product),
                          ('order_id.pricelist_id', '=', pricelist),
                          ('price_unit', '!=', -1)]
                last_id = self.search(cr, uid, domain, limit=1,
                                      order="id desc")
                if last_id:
                    line = self.browse(cr, uid, last_id[0], context)
                    res['value']['last_price_fresh'] = line.price_unit
        return res


class res_partner(osv.Model):
    _inherit = "res.partner"

    def get_visibele_products_names(self, cr, uid, partner_id, context=None):
        """ Return a dict with id of client and an array of his products
            names"""
        t_product = self.pool.get("product.product")
        if context is None:
            context = {}
        context.update({'partner_id': partner_id})
        product_ids = t_product.search(cr, uid, [], context=context)
        product_names = []
        product_codes = []
        if context.get('partner_id', False):
            for prod_obj in t_product.browse(cr, uid, product_ids,
                                             context=context):
                product_names.append(prod_obj.name)
                product_codes.append(prod_obj.default_code)
            return {context['partner_id']: [product_names, product_codes]}
        else:
            return product_ids

    _columns = {
        'contact_id': fields.many2one('res.partner', 'Contact',
                                      domain=[('customer', '=', True)]),
    }


class product_product(osv.Model):
    _inherit = "product.product"

    def get_product_info(self, cr, uid, product_id, partner_id, pricelist_id,
                         context=None):
        """ return data of widget productInfo"""
        if context is None:
            context = {}
        res = {'stock': "-",
               'last_date': "-",
               'last_qty': "-",
               'last_price': "-",
               'prodct_mark': "-",
               'prodct_class': "-",
               'weight_unit': "-",
               'min_price': "-",
               'product_margin': "-",
               'discount': "-",
               'n_line': "-"}
        t_sol = self.pool.get("sale.order.line")
        t_pricelist = self.pool.get("product.pricelist")
        if not product_id or not partner_id:
            raise osv.except_osv(_('Error!'), _("product_id or partrner_id\
                                                 must be defined"))
        product_obj = self.browse(cr, uid, product_id, context=context)
        res['stock'] = str(product_obj.virtual_stock_conservative)

        res['product_mark'] = product_obj.mark or "-"
        res['product_class'] = product_obj.product_class or "-"
        res['weight_unit'] = product_obj.weight or "0.00"
        domain = [('product_id', '=', product_id),
                  ('order_id.partner_id', '=', partner_id),
                  ('state', 'in', ['confirmed', 'done']),
                  ('order_id.telesale', '=', True)]
        line_ids = t_sol.search(cr, uid, domain, context=context, limit=1,
                                order="id desc")
        if line_ids:  # Last sale info
            line_obj = t_sol.browse(cr, uid, line_ids[0], context=context)
            res['last_date'] = line_obj.order_id.date_order
            res['last_qty'] = str(line_obj.product_uom_qty)
            res['last_price'] = str(line_obj.price_unit)
        # Calc min price
        min_price = 0
        if product_obj.product_class in ['dry', 'frozen', 'chilled']:
            min_price = t_pricelist._get_product_pvp(cr, uid, product_id,
                                                     pricelist_id)[1]
        res['min_price'] = min_price and str(min_price) or "0.00"
        return res


class product_template(osv.Model):
    _inherit = 'product.template'

    def _stock_conservative(self, cr, uid, ids, field_names=None,
                            arg=False, context=None):
        """ Finds the outgoing quantity of product.
        @return: Dictionary of values
        """
        if not field_names:
            field_names = []
        if context is None:
            context = {}
        res = {}
        prod = self.pool.get('product.template')
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        if 'virtual_stock_conservative' in field_names:
            # Virtual stock conservative = real qty + outgoing qty
            for id in ids:
                realqty = prod.browse(cr,
                                      uid,
                                      id,
                                      context=context).qty_available
                outqty = prod.browse(cr,
                                     uid,
                                     id,
                                     context=context).outgoing_qty
                res[id] = realqty + outqty
        return res

    _columns = {
        'virtual_stock_conservative': fields.function(_stock_conservative,
                                                      type='float',
                                                      string='Virtual \
                                                              Stock \
                                                              Conservative'),
    }


class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"

    def _get_invoice_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        model = context.get('active_model')
        if not model or 'stock.picking' not in model:
            return []

        model_pool = self.pool.get(model)
        res_ids = context and context.get('active_ids', [])
        browse_picking = model_pool.browse(cr, uid, res_ids, context=context)
        for pick in browse_picking:
            type = pick.picking_type_id.code
            if type == 'outgoing' and pick.sale_id:
                return pick.sale_id.date_invoice
        return False

    _defaults = {
        'invoice_date': _get_invoice_date,
    }


class crm_phonecall(osv.Model):
    """ Overwrite to add new state 'calling' in order to know if a call is in
        course in telesale UI
    """

    _inherit = 'crm.phonecall'
    _columns = {
        'state': fields.selection([('draft', 'Draft'),
                                   ('open', 'Confirmed'),
                                   ('calling', 'In Course'),
                                   ('pending', 'Not Held'),
                                   ('cancel', 'Cancelled'),
                                   ('done', 'Held')],
                                  string='Status', size=16, readonly=True,
                                  track_visibility='onchange',)
    }


class product_uom(osv.Model):
    """
    like_type field let the sistem know wich is the unit type.
    It defines units, kg, boxes, mantles and palets.
    """
    _inherit = "product.uom"

    _columns = {
        'like_type': fields.selection([('units', 'Units'),
                                       ('kg', 'Kg'),
                                       ('boxes', 'Boxes'),
                                       ('mantles', 'Mantles'),
                                       ('palets', 'Palets')], 'Equals to'),
    }
    _defaults = {
        'like_type': '',
    }

    # _sql_constraints = [
    #     ('like_type_uniq', 'unique(like_type)',
    #      _("Field Equals to is already setted"))
    # ]


class res_company(osv.Model):
    _inherit = 'res.company'

    _columns = {
        'min_limit': fields.float('Minimum Limit',
                                  digits_compute=
                                  dp.get_precision('Product Price')),
        'min_margin': fields.float('Minimum Margin',
                                   digits_compute=
                                   dp.get_precision('Product Price')),
    }
