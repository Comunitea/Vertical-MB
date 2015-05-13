# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
from openerp import api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


class purchase_order(osv.Model):
    _inherit = "purchase.order"

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'amount_discounted': 0.0,
            }
            dis = val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                dis += (line.price_unit - line.price_unit_promotion) * \
                    line.product_qty
                val1 += line.price_subtotal
                for c in tax_obj.compute_all(cr, uid, line.taxes_id,
                                             line.price_unit_promotion,
                                             line.product_qty, line.product_id,
                                             order.partner_id)['taxes']:
                    val += c.get('amount', 0.0)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + \
                res[order.id]['amount_tax']
            res[order.id]['amount_discounted'] = dis
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        line_obj = self.pool.get('purchase.order.line')
        for line in line_obj.browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'amount_untaxed': fields.function(_amount_all,
                                          digits_compute=dp.get_precision('Account'),
                                          string='Untaxed Amount',
                                          store={
                                              'purchase.order.line':
                                                 (_get_order, None, 10),
                                          }, multi="sums",
                                          help="The amount without tax",
                                          track_visibility='always'),
        'amount_tax': fields.function(_amount_all,
                                      digits_compute=dp.get_precision('Account'),
                                      string='Taxes',
                                      store={
                                          'purchase.order.line':
                                             (_get_order, None, 10),
                                      }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all,
                                        digits_compute=dp.get_precision('Account'),
                                        string='Total',
                                        store={
                                            'purchase.order.line':
                                                (_get_order, None, 10),
                                        }, multi="sums",
                                        help="The total amount"),
        'amount_discounted': fields.function(_amount_all,
                                             digits_compute=dp.get_precision('Account'),
                                             string='Discount',
                                             store={
                                                 'purchase.order.line':
                                                     (_get_order, None, 10),
                                             }, multi="sums",
                                             help="The Total discount"),
    }

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        promo_obj = self.pool.get('partner.promotion')
        res = super(purchase_order, self)._prepare_inv_line(cr, uid,
                                                            account_id,
                                                            order_line,
                                                            context)
        res['discount_ids'] = \
            promo_obj._get_invoice_discounts(cr, uid, order_line.product_id.id,
                                             order_line.order_id.partner_id.id,
                                             order_line.order_id.date_order,
                                             'line', context)
        return res

    def action_invoice_create(self, cr, uid, ids, context=None):
        """Generates invoice for given ids of purchase orders and
            links that invoice ID to purchase order.
        :param ids: list of ids of purchase orders.
        :return: ID of created invoice.
        :rtype: int
        """
        if context is None:
            context = {}
        promo_obj = self.pool.get('partner.promotion')
        journal_obj = self.pool.get('account.journal')
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        us_obj = self.pool.get('res.users')

        res = False
        uid_company_id = us_obj.browse(cr, uid, uid,
                                       context=context).company_id.id
        for order in self.browse(cr, uid, ids, context=context):
            context.pop('force_company', None)
            if order.company_id.id != uid_company_id:
                # if the company of the document is different than the \
                # current user company, force the company in the context \
                # then re-do a browse to read the property fields for the
                # good company.
                context['force_company'] = order.company_id.id
                order = self.browse(cr, uid, order.id, context=context)
            pay_acc_id = order.partner_id.property_account_payable.id
            journal_ids = journal_obj.search(cr, uid,
                                             [('type', '=', 'purchase'),
                                              ('company_id', '=',
                                               order.company_id.id)],
                                             limit=1)
            if not journal_ids:
                raise osv.except_osv(_('Error!'),
                                     _('Define purchase journal for \
                                       this company: "%s" (id:%d).') %
                                     (order.company_id.name,
                                      order.company_id.id))

            # generate invoice line correspond to PO line and
            # link that to created invoice (inv_id) and PO line
            inv_lines = []
            for po_line in order.order_line:
                acc_id = self._choose_account_from_po_line(cr, uid, po_line,
                                                           context=context)
                inv_line_data = self._prepare_inv_line(cr, uid, acc_id,
                                                       po_line,
                                                       context=context)
                inv_line_id = inv_line_obj.create(cr, uid, inv_line_data,
                                                  context=context)
                inv_lines.append(inv_line_id)

                po_line.write({'invoiced': True,
                               'invoice_lines': [(4, inv_line_id)]},
                              context=context)

            # get invoice data and create invoice
            inv_data = {
                'name': order.partner_ref or order.name,
                'reference': order.partner_ref or order.name,
                'account_id': pay_acc_id,
                'type': 'in_invoice',
                'partner_id': order.partner_id.id,
                'currency_id': order.pricelist_id.currency_id.id,
                'journal_id': len(journal_ids) and journal_ids[0] or False,
                'invoice_line': [(6, 0, inv_lines)],
                'origin': order.name,
                'fiscal_position': order.fiscal_position.id or False,
                'payment_term': order.payment_term_id.id or False,
                'company_id': order.company_id.id,
                'discount_ids':
                    promo_obj._get_invoice_discounts(cr, uid, False,
                                                     order.partner_id.id,
                                                     order.date_order,
                                                     'global', context),
            }
            inv_id = inv_obj.create(cr, uid, inv_data, context=context)

            # compute the invoice
            inv_obj.button_compute(cr, uid, [inv_id], context=context,
                                   set_total=True)

            # Link this new invoice to related purchase order
            order.write({'invoice_ids': [(4, inv_id)]}, context=context)
            res = inv_id
        return res


class purchase_order_line(osv.Model):
    _inherit = "purchase.order.line"

    def _get_price_unit_promotion(self, cr, uid, ids, field_name, arg,
                                  context=None):
        res = {}
        promo_obj = self.pool.get('partner.promotion.rel')
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = line.price_unit
            context = dict(context)
            context.update({'type_promo': 'purchase',
                            'domain_promotion': 'all'})
            applieds = promo_obj.get_applied_promos(cr, uid,
                                                    line.product_id.id or
                                                    False,
                                                    line.order_id.partner_id.id,
                                                    line.order_id.date_order,
                                                    context)
            discount = 0.0
            for applied in promo_obj.browse(cr, uid, applieds['accumulated'],
                                            context):
                discount += res[line.id] * (applied.promotion_id.discount /
                                            100)
            res[line.id] -= discount
            for applied in promo_obj.browse(cr, uid, applieds['sequence'],
                                            context):
                res[line.id] -= res[line.id] * (applied.promotion_id.discount /
                                                100)
            res[line.id] = res[line.id]
        return res

    _columns = {
        'price_unit_promotion': fields.function(_get_price_unit_promotion,
                                                type='float', method=True,
                                                digits_compute= dp.get_precision('Logistic Quota'),
                                                string="Unit price with \
                                                        promotion"),
    }

from openerp import models, fields, api

class purchase_order_line2(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _amount_line(self):
        """
        Overrides midban_ultra_fresh _amount_line.
        """
        for line in self:
            qty = line.ultrafresh_po and line.purchased_kg or line.product_qty
            price = line.price_unit_promotion
            taxes = line.taxes_id.compute_all(price, qty, line.product_id,
                                              line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            line.price_subtotal = cur.round(taxes['total'])

    price_subtotal = fields.Float('Subtotal', compute=_amount_line,
                                  required=True, readonly=True,
                                  digits_compute=
                                  dp.get_precision('Account'))
