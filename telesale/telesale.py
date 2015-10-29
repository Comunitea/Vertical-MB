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

    def search_prod2shell_by_partner(self, cr, uid, ids, context=None):
        if not ids:
            ids = self.search(cr, uid, [('customer', '=', True),
                                        ('state2', '=', 'registered')])
        res = {}
        for part in self.browse(cr, uid, ids):
            res[part.id] = self.search_products_to_sell(cr, uid, part.id,
                                                        context)
        return res

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
        res = {'stock': 0.0,
               'last_date': "-",
               'last_qty': 0.0,
               'last_price': 0.0,
               'product_mark': "-",
               'product_class': "-",
               'weight_unit': 0.0,
               'min_price': 0.0,
               'product_margin': 0.0,
               'discount': 0.0,
               'max_discount': 0.0,
               'n_line': "-"}
        t_sol = self.pool.get("sale.order.line")
        t_pricelist = self.pool.get("product.pricelist")
        if not product_id or not partner_id:
            raise osv.except_osv(_('Error!'), _("product_id or partrner_id\
                                                 must be defined"))
        product_obj = self.browse(cr, uid, product_id, context=context)
        res['stock'] = product_obj.virtual_stock_conservative
        res['product_mark'] = product_obj.mark or "-"
        res['product_class'] = product_obj.product_class or "-"
        res['max_discount'] = product_obj.max_discount and \
            product_obj.max_discount or product_obj.category_max_discount
        res['weight_unit'] = product_obj.weight or "0.00"
        domain = [('product_id', '=', product_id),
                  ('order_id.partner_id', '=', partner_id),
                  ('state', 'in', ['confirmed', 'done']),
                  ]
                #   ('order_id.chanel', '=', 'telesale')]
        line_ids = t_sol.search(cr, uid, domain, context=context, limit=1,
                                order="id desc")
        if line_ids:  # Last sale info
            line_obj = t_sol.browse(cr, uid, line_ids[0], context=context)
            res['last_date'] = line_obj.order_id.date_order
            res['last_qty'] = line_obj.product_uom_qty
            res['last_price'] = line_obj.price_unit
        # Calc min price, SE elimino price_system_variable, esto ya no es así
        min_price = 0.0
        # if product_obj.product_class == 'normal':
        #     min_price = t_pricelist._get_product_pvp(cr, uid, product_id,
        #                                              pricelist_id)[1]
        res['min_price'] = min_price
        return res


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
                                   ('open', 'Pending'),
                                   ('calling', 'In Course'),
                                   ('pending', 'No response'),
                                   ('cancel', 'Cancelled'),
                                   ('done', 'Held')],
                                  string='Status', size=16, readonly=True,
                                  track_visibility='onchange',)
    }


class res_company(osv.Model):
    _inherit = 'res.company'

    _columns = {
        'min_limit': fields.float('Minimum Limit',
                                  digits_compute=dp.get_precision
                                  ('Product Price')),
        'min_margin': fields.float('Minimum Margin',
                                   digits_compute=dp.get_precision
                                   ('Product Price')),
    }


class StockReservation(osv.Model):
    _inherit = 'stock.reservation'

    def create_reserve_from_ui(self, cr, uid, reserve_id, qty, context=None):
        """
        Equals to launch wizard from a reserve record, clicking the button
        create order
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({
            'active_model': 'stock.reservation',
            'active_ids': [reserve_id]
        })
        t_wzd = self.pool.get("sale.from.reserve.wzd")
        vals = {'qty': qty, 'chanel': 'telesale'}
        wzd_id = t_wzd.create(cr, uid, vals, context=ctx)
        wzd_obj = t_wzd.browse(cr, uid, wzd_id, context=ctx)
        wzd_obj.create_sale()
        return True
