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
from openerp import netsvc, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
from datetime import date, timedelta


class sale(osv.osv):
    """ Overwrited to add a chanel field and margin
    """
    _inherit = 'sale.order'

    def _get_total_margin(self, cr, uid, ids, field_name, args,
                          context=None):
        """
        Get the margins against standard_price instead of cmc field defined
        in price system variable
        """
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            cur = order.pricelist_id.currency_id
            res[order.id] = {
                'total_margin': 0.0,
                'total_margin_per': 0.0,
            }
            # sum_cmc = 0
            # sum_margin = 0
            # for line in order.order_line:
            #     qty = line.choose_unit == 'box' and line.product_uos_qty or \
            #         line.product_uom_qty
            #     prod_cmc = line.product_id.cmc
            #     sum_cmc += line.product_id.cmc * qty
            #     pvp = line.price_unit
            #     sum_margin += (pvp - prod_cmc) * qty

            # total_margin = cur_obj.round(cr, uid, cur, sum_margin)
            # res[order.id]['total_margin'] = total_margin
            # if order.amount_untaxed:
            #     op = (order.amount_untaxed - sum_cmc) / order.amount_untaxed
            #     total_margin_per = cur_obj.round(cr, uid, cur, op * 100)
            #     res[order.id]['total_margin_per'] = total_margin_per
            sum_cost = 0
            sum_margin = 0
            for line in order.order_line:
                prod_cost = line.product_id.standard_price
                sum_cost += prod_cost * line.product_uom_qty
                pvp = line.price_unit
                if line.discount:
                    pvp = pvp * (1 - line.discount / 100.0)
                sum_margin += (pvp - prod_cost) * line.product_uom_qty

            total_margin = cur_obj.round(cr, uid, cur, sum_margin)
            res[order.id]['total_margin'] = total_margin
            if order.amount_untaxed:
                op = (order.amount_untaxed - sum_cost) / order.amount_untaxed
                total_margin_per = cur_obj.round(cr, uid, cur, op * 100)
                res[order.id]['total_margin_per'] = total_margin_per
        return res

    _columns = {
        'chanel': fields.selection([('erp', 'ERP'), ('telesale', 'telesale'),
                                    ('tablet', 'Tablet'),
                                    ('other', 'Other'),
                                    ('ecomerce', 'E-comerce')], 'Chanel',
                                   readonly=True),
        'date_invoice': fields.date('Date Invoice', readonly=True),
        'total_margin': fields.function(_get_total_margin, type="float",
                                        string="Total Margin",
                                        multi="mar",
                                        digits_compute=dp.get_precision
                                        ('Account'),
                                        readonly=True),
        'total_margin_per': fields.function(_get_total_margin, type="float",
                                            string="Margin Percentage",
                                            multi="mar",
                                            digits_compute=dp.get_precision
                                            ('Account'),
                                            readonly=True),
    }

    _defaults = {
        'chanel': 'erp'
    }

    def create_order_from_ui(self, cr, uid, orders, context=None):
        t_partner = self.pool.get("res.partner")
        t_order = self.pool.get("sale.order")
        t_order_line = self.pool.get("sale.order.line")
        t_product = self.pool.get("product.product")
        t_sequence = self.pool.get("ir.sequence")
        order_ids = []
        create_mail = False
        if context is None:
            context = {}

        for rec in orders:
            order = rec['data']
            if order['erp_id'] and order['erp_state'] != 'draft':

                # raise osv.except_osv(_('Error!'), _("Combination error!"))
                self.cancel_sale_to_draft(cr, uid, order['erp_id'], context)
                order['erp_state'] = 'draft'
            partner_obj = t_partner.browse(cr, uid, order['partner_id'])
            vals = {
                'partner_id': partner_obj.id,
                'pricelist_id': partner_obj.property_product_pricelist.id,
                'partner_invoice_id': partner_obj.id,
                'partner_shipping_id': partner_obj.id,
                'chanel': 'telesale',
                'order_policy': 'picking',
                'date_invoice': order['date_invoice'] or False,
                'date_order': time.strftime("%Y-%m-%d %H:%M:%S"),
                'date_planned':
                'date_planned' in order and order['date_planned'] + " 19:00:00"
                or False,
                'note': 'note' in order and order['note'] or False,
                'customer_comment': 'customer_comment' in order and order['customer_comment'] or False,
                # 'name': t_sequence.get(cr, uid, 'telesale.order') or '/',
                'supplier_id': 'supplier_id' in order and order['supplier_id'] or False
            }
            if order['erp_id'] and order['erp_state'] == 'draft':
                order_obj = t_order.browse(cr, uid, order['erp_id'], context)
                if 'note' in order and order['note'] and (order_obj.note != order['note']):
                    create_mail = True
                t_order.write(cr, uid, [order['erp_id']], vals)
                order_id = order['erp_id']
            else:
                vals['name'] = t_sequence.get(cr, uid, 'telesale.order') or '/'
                order_id = t_order.create(cr, uid, vals)
                if order['note']:
                    create_mail = True
            if create_mail:
                vals = {
                    'body': order['note'],
                    'model': 'sale.order',
                    'res_id': order_id,
                    'type': 'email'
                }


                self.pool.get('mail.message').create(cr, uid, vals,
                                                     context=context)

            order_ids.append(order_id)

            order_lines = order['lines']
            t_data = self.pool.get('ir.model.data')
            xml_id_name = 'midban_product.product_uom_box'
            if order['erp_id'] and order['erp_state'] == 'draft':
                domain = [('order_id', '=', order_id)]
                line_ids = t_order_line.search(cr, uid, domain)
                t_order_line.unlink(cr, uid, line_ids)
            for line in order_lines:
                product_obj = t_product.browse(cr, uid, line['product_id'])
                product_uom_id = line.get('product_uom', False)
                product_uom_qty = line.get('qty', 0.0)

                product_uos_id = line.get('product_uos', False)
                product_uos_qty = line.get('product_uos_qty', 0.0)
                vals = {
                    'order_id': order_id,
                    'name': product_obj.name,
                    'product_id': product_obj.id,
                    'price_unit': line.get('price_unit', 0.0),
                    'price_udv': line.get('price_udv', 0.0),
                    'product_uom': product_uom_id,
                    'product_uos': product_uos_id,
                    'product_uom_qty': product_uom_qty,
                    'product_uos_qty': product_uos_qty,
                    'tax_id': [(6, 0, line.get('tax_ids', False))],
                    'pvp_ref': line.get('pvp_ref', 0.0),
                    'q_note': line.get('qnote', False),
                    'detail_note': line.get('detail_note', False),
                    'discount': line.get('discount', 0.0)
                }

                t_order_line.create(cr, uid, vals)
            if order['action_button'] == 'confirm':
                # wf_service = netsvc.LocalService('workflow')
                # wf_service.trg_validate(uid, 'sale.order', order_id,
                #                         'order_confirm', cr)
                self.action_button_confirm(cr, uid, [order_id],
                                           context=context)
            elif order['action_button'] == 'confirm_background':
                # wf_service = netsvc.LocalService('workflow')
                # wf_service.trg_validate(uid, 'sale.order', order_id,
                #                         'order_confirm', cr)
                self.action_button_confirm_thread(cr, uid, [order_id],
                                                  context=context)

            if 'set_promotion' in order and order['set_promotion']:
                self.apply_promotions(cr, uid, [order_id], context=context)
        return order_ids

    def cancel_order_from_ui(self, cr, uid, order_id, context=None):
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'sale.order', order_id[0], 'cancel', cr)
        return True


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
            # result = t_priclist._get_product_pvp(cr, uid, line.product_id.id,
            #                                      pricelist_id)
            price = t_priclist.price_get(cr, uid, [pricelist_id],
                                         line.product_id.id,
                                         line.product_uom_qty or 1.0,
                                         line.order_id.partner_id.id,
                                         {'uom': line.product_uom.id,
                                          'date': line.order_id.date_order})

            res[line.id] = price and price[pricelist_id] or 0.0
        return res

    _columns = {
        'pvp_ref': fields.float('PVP ref',
                                digits_compute=dp.get_precision
                                ('Product Price'),
                                readonly=True),
        'last_price_fresh': fields.float('Last Price Fresh',
                                         digits_compute=dp.get_precision
                                         ('Product Price'),
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
                                    qty=qty, uom=uom, qty_uos=qty_uos, uos=uos,
                                    name=name, partner_id=partner_id,
                                    lang=lang, update_tax=update_tax,
                                    date_order=date_order,
                                    packaging=packaging,
                                    fiscal_position=fiscal_position,
                                    flag=flag, context=context)
        res['value']['last_price_fresh'] = 0.0
        if product and pricelist:
            prod_obj = t_product.browse(cr, uid, product, context)
            if prod_obj.product_class in ["fresh", "ultrafresh"]:
                domain = [('product_id', '=', product),
                          ('order_id.pricelist_id', '=', pricelist),
                          ('price_unit', '!=', -1)]
                last_id = self.search(cr, uid, domain, limit=1,
                                      order="id desc")
                if last_id:
                    line = self.browse(cr, uid, last_id[0], context)
                    res['value']['last_price_fresh'] = line.price_unit
        return res

    @api.model
    def get_last_lines_by(self, period, client_id):
        """
        """
        cr = self._cr
        date_str = date.today()
        if period == "ult":
            SQ = """ SELECT id
                     FROM sale_order_line sol
                     WHERE order_id in
                        (SELECT id
                         FROM sale_order WHERE
                         state in ('progress','manual','done','history')
                         and partner_id = %s order by id desc limit 1)
                    ORDER BY id desc"""

        else:
            if period == "3month":
                date_str = date.today() - timedelta(90)
            elif period == "year":
                date_str = date.today() - timedelta(365)
            date_str = date_str.strftime("%Y-%m-%d %H:%M:%S")
            SQ = """ SELECT * FROM
                        (SELECT distinct on (product_id) sol.id
                         FROM sale_order_line sol
                         INNER JOIN sale_order so ON so.id = sol.order_id
                         WHERE so.state in
                            ('progress','manual','done','history')
                         AND so.partner_id = %s
                         AND so.date_order >= %s
                         ORDER BY product_id desc, id desc) AS SQ
                    ORDER BY id desc"""

        if period != 'ult':
            cr.execute(SQ, (client_id, date_str))
        else:
            cr.execute(SQ, (client_id,))
        fetch = cr.fetchall()
        prod_ids = [x[0] for x in fetch]
        res = []
        for l in self.browse(prod_ids):
            # Avoid not registered products
            # if l.product_id.state2 != 'registered':
            #     continue
            # dic = {
            #     'order_id': l.order_id.id,
            #     'product_id': (l.product_id.id, l.product_id.name),
            #     'product_uom': (l.product_uom.id, l.product_uom.name),
            #     'product_uom_qty': l.product_uom_qty,
            #     'product_uos': (l.product_uos.id, l.product_uos.name),
            #     'product_uos_qty': l.product_uos_qty,
            #     'price_udv': l.price_udv,
            #     'price_unit': l.price_unit,
            #     'discount': l.discount,
            #     'price_subtotal': l.product_uom_qty * l.price_unit *
            #     (1 - (l.discount / 100.0)),
            #     'tax_id': [x.id for x in l.tax_id],
            #     'pvp_ref': l.pvp_ref,
            #     'current_pvp': l.current_pvp,
            #     'q_note': l.q_note.name,
            #     'detail_note': l.detail_note
            # }
            dic = {
                'product_id': (l.product_id.id, l.product_id.name),
                'price_unit': l.product_id.list_price,
                'default_code': l.product_id.default_code or \
                l.product_id.default_code2
            }
            res.append(dic)
        return res
