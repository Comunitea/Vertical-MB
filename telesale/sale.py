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
from openerp import netsvc
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class sale(osv.osv):
    """ Overwrited to add a boolean 'telesale' to recognise telesale orders.
    """
    _inherit = 'sale.order'

    def _get_total_margin(self, cr, uid, ids, field_name, args,
                          context=None):
        """
        Get the margins against cmc.
        """
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            cur = order.pricelist_id.currency_id
            res[order.id] = {
                'total_margin': 0.0,
                'total_margin_per': 0.0,
            }
            sum_cmc = 0
            sum_margin = 0
            for line in order.order_line:
                prod_cmc = line.product_id.cmc
                sum_cmc += line.product_id.cmc * line.product_uom_qty
                pvp = line.price_unit
                sum_margin += (pvp - prod_cmc) * line.product_uom_qty

            total_margin = cur_obj.round(cr, uid, cur, sum_margin)
            res[order.id]['total_margin'] = total_margin
            if order.amount_untaxed:
                op = (order.amount_untaxed - sum_cmc) / order.amount_untaxed
                total_margin_per = cur_obj.round(cr, uid, cur, op * 100)
                res[order.id]['total_margin_per'] = total_margin_per
        return res

    _columns = {
        'telesale': fields.boolean('Telesale order', readonly=True),
        'date_invoice': fields.date('Date Invoice', readonly=True),
        'total_margin': fields.function(_get_total_margin, type="float",
                                        string="Total Margin",
                                        multi="mar",
                                        digits_compute=
                                        dp.get_precision('Account'),
                                        readonly=True),
        'total_margin_per': fields.function(_get_total_margin, type="float",
                                            string="Margin Percentage",
                                            multi="mar",
                                            digits_compute=
                                            dp.get_precision('Account'),
                                            readonly=True),
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
                raise osv.except_osv(_('Error!'), _("Combination error!"))
            partner_obj = t_partner.browse(cr, uid, order['partner_id'])
            vals = {
                'partner_id': partner_obj.id,
                'pricelist_id': partner_obj.property_product_pricelist.id,
                'partner_invoice_id': partner_obj.id,
                'partner_shipping_id': partner_obj.id,
                'telesale': True,
                'order_policy': 'picking',
                'date_invoice': order['date_invoice'] or False,
                'note': order['note'] or False,
                'name': t_sequence.get(cr, uid, 'telesale.order') or '/',
            }
            if order['erp_id'] and order['erp_state'] == 'draft':
                order_obj = t_order.browse(cr, uid, order['erp_id'], context)
                if order['note'] and (order_obj.note != order['note']):
                    create_mail = True
                t_order.write(cr, uid, [order['erp_id']], vals)
                order_id = order['erp_id']
            else:
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
            for line in order_lines:
                product_obj = t_product.browse(cr, uid, line['product_id'])
                vals = {
                    'order_id': order_id,
                    'name': product_obj.name,
                    'product_id': product_obj.id,
                    'price_unit': line['price_unit'],
                    'product_uom': line['product_uom'],
                    'product_uom_qty': line['qty'],
                    'tax_id': [(6, 0, line['tax_ids'])],
                    'pvp_ref': line['pvp_ref'],
                }
                if order['erp_id'] and order['erp_state'] == 'draft':
                    domain = [('order_id', '=', order_id)]
                    line_ids = t_order_line.search(cr, uid, domain)
                    t_order_line.unlink(cr, uid, line_ids)
                t_order_line.create(cr, uid, vals)
            if order['action_button'] == 'confirm':
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'sale.order', order_id,
                                        'order_confirm', cr)
        return order_ids

    def cancel_order_from_ui(self, cr, uid, order_id, context=None):
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'sale.order', order_id[0], 'cancel', cr)
        return True
