# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra$ <omar@comunitea.com>
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

from openerp import models, api, fields


class purchase_order(models.Model):
    _inherit = "purchase.order"

    @api.depends("amount_untaxed", "order_line.price_unit",
                 "order_line.discount", "order_line.product_qty")
    @api.one
    def _get_amount_discounted(self):
        gross_amount = 0.0
        for line in self.order_line:
            gross_amount += line.product_qty * line.price_unit

        self.amount_discounted = gross_amount - self.amount_untaxed

    amount_discounted = fields.Float("Amount discounted", readonly=True,
                                     compute=_get_amount_discounted,
                                     store=True, help="The Total discount")


    #TODO: Mover al módulo de edi que es el que crea los descuentos en la
    # factura
    #~ def _prepare_inv_line(self, cr, uid, account_id, order_line,
                             #~ context=None):
        #~ promo_obj = self.pool.get('partner.promotion')
        #~ res = super(purchase_order, self)._prepare_inv_line(cr, uid,
                                                            #~ account_id,
                                                            #~ order_line,
                                                            #~ context)
        #~ res['discount_ids'] = \
            #~ promo_obj._get_invoice_discounts(cr, uid,
                                                #~ order_line.product_id.id,
                                    #~ order_line.order_id.partner_id.id,
                                             #~ order_line.order_id.date_order,
                                             #~ 'line', context)
        #~ return res

    #~ def action_invoice_create(self, cr, uid, ids, context=None):
        #~ """Generates invoice for given ids of purchase orders and
            #~ links that invoice ID to purchase order.
        #~ :param ids: list of ids of purchase orders.
        #~ :return: ID of created invoice.
        #~ :rtype: int
        #~ """
        #~ if context is None:
            #~ context = {}
        #~ promo_obj = self.pool.get('partner.promotion')
        #~ journal_obj = self.pool.get('account.journal')
        #~ inv_obj = self.pool.get('account.invoice')
        #~ inv_line_obj = self.pool.get('account.invoice.line')
        #~ us_obj = self.pool.get('res.users')
#~
        #~ res = False
        #~ uid_company_id = us_obj.browse(cr, uid, uid,
                                       #~ context=context).company_id.id
        #~ for order in self.browse(cr, uid, ids, context=context):
            #~ context.pop('force_company', None)
            #~ if order.company_id.id != uid_company_id:
                #~ # if the company of the document is different than the \
                #~ # current user company, force the company in the context \
                #~ # then re-do a browse to read the property fields for the
                #~ # good company.
                #~ context['force_company'] = order.company_id.id
                #~ order = self.browse(cr, uid, order.id, context=context)
            #~ pay_acc_id = order.partner_id.property_account_payable.id
            #~ journal_ids = journal_obj.search(cr, uid,
                                             #~ [('type', '=', 'purchase'),
                                              #~ ('company_id', '=',
                                               #~ order.company_id.id)],
                                             #~ limit=1)
            #~ if not journal_ids:
                #~ raise osv.except_osv(_('Error!'),
                                     #~ _('Define purchase journal for \
                                       #~ this company: "%s" (id:%d).') %
                                     #~ (order.company_id.name,
                                      #~ order.company_id.id))
#~
            #~ # generate invoice line correspond to PO line and
            #~ # link that to created invoice (inv_id) and PO line
            #~ inv_lines = []
            #~ for po_line in order.order_line:
                #~ acc_id = self._choose_account_from_po_line(cr, uid, po_line,
                                                           #~ context=context)
                #~ inv_line_data = self._prepare_inv_line(cr, uid, acc_id,
                                                       #~ po_line,
                                                       #~ context=context)
                #~ inv_line_id = inv_line_obj.create(cr, uid, inv_line_data,
                                                  #~ context=context)
                #~ inv_lines.append(inv_line_id)
#~
                #~ po_line.write({'invoiced': True,
                               #~ 'invoice_lines': [(4, inv_line_id)]},
                              #~ context=context)
#~
            #~ # get invoice data and create invoice
            #~ inv_data = {
                #~ 'name': order.partner_ref or order.name,
                #~ 'reference': order.partner_ref or order.name,
                #~ 'account_id': pay_acc_id,
                #~ 'type': 'in_invoice',
                #~ 'partner_id': order.partner_id.id,
                #~ 'currency_id': order.pricelist_id.currency_id.id,
                #~ 'journal_id': len(journal_ids) and journal_ids[0] or False,
                #~ 'invoice_line': [(6, 0, inv_lines)],
                #~ 'origin': order.name,
                #~ 'fiscal_position': order.fiscal_position.id or False,
                #~ 'payment_term': order.payment_term_id.id or False,
                #~ 'company_id': order.company_id.id,
                #~ 'discount_ids':
                    #~ promo_obj._get_invoice_discounts(cr, uid, False,
                                                     #~ order.partner_id.id,
                                                     #~ order.date_order,
                                                     #~ 'global', context),
            #~ }
            #~ inv_id = inv_obj.create(cr, uid, inv_data, context=context)
#~
            #~ # compute the invoice
            #~ inv_obj.button_compute(cr, uid, [inv_id], context=context,
                                   #~ set_total=True)
#~
            #~ # Link this new invoice to related purchase order
            #~ order.write({'invoice_ids': [(4, inv_id)]}, context=context)
            #~ res = inv_id
        #~ return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty,
                            uom_id, partner_id, date_order=False,
                            fiscal_position_id=False, date_planned=False,
                            name=False, price_unit=False, state='draft',
                            context=None):
        if context is None:
            context = {}
        sup = super(PurchaseOrderLine, self)
        res = sup.onchange_product_id(cr, uid, ids, pricelist_id, product_id,
                                      qty, uom_id, partner_id,
                                      context=context,
                                      date_order=date_order,
                                      fiscal_position_id=fiscal_position_id,
                                      date_planned=date_planned,
                                      name=name,
                                      price_unit=price_unit,
                                      state=state)
        if res.get('value', False) and res['value'].get('price_unit', False):
            promo_obj = self.pool.get('partner.promotion.rel')
            ctx = dict(context)
            ctx.update({'type_promo': 'purchase',
                        'domain_promotion': 'all'})
            price_disc = res['value']['price_unit']
            applieds = promo_obj.get_applied_promos(cr, uid,
                                                    product_id or
                                                    False, partner_id,
                                                    date_order, ctx)
            discount = 0.0
            for applied in promo_obj.browse(cr, uid, applieds['accumulated'],
                                            ctx):
                discount += price_disc * (applied.promotion_id.discount /
                                          100.0)
            price_disc -= discount
            for applied in promo_obj.browse(cr, uid, applieds['sequence'],
                                            ctx):
                price_disc -= price_disc * (applied.promotion_id.discount /
                                            100.0)
            if price_disc != res['value']['price_unit']:
                res['value']['discount'] = 100.0 - ((price_disc * 100.0) /
                                                    res['value']['price_unit'])

        return res

