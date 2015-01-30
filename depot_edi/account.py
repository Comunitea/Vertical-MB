# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Pexego Sistemas Informáticos All Rights Reserved
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
from openerp.tools.translate import _
from openerp.exceptions import except_orm


class account_tax(models.Model):
    """
    Add generic fields
    """
    _inherit = 'account.tax'

    code = fields.Char('Code', help="Code of tax for EDI files")


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    document_id = fields.Many2one('edi.doc', 'EDI Document')
    name_doc = fields.Char('Ref', readonly=True, related='document_id.name')
    file_name_doc = fields.Char('File Name', readonly=True,
                                related='document_id.file_name')
    date_doc = fields.Datetime('Downloaded', readonly=True,
                               related='document_id.date')
    date_process_doc = fields.Datetime('Downloaded', readonly=True,
                                       related='document_id.date_process')
    state_doc = fields.Selection('State', readonly=True,
                                 related='document_id.state')
    message = fields.Text('Messagge', readonly=True,
                          related='document_id.message')
    state = fields.Selection([('draft', 'Draft'),
                              ('received', 'Received'),
                              ('proforma', 'Pro-forma'),
                              ('proforma2', 'Pro-forma'),
                              ('open', 'Open'),
                              ('paid', 'Paid'),
                              ('cancel', 'Cancelled')], string='Status',
                             index=True, readonly=True, default='draft',
                             track_visibility='onchange', copy=False,
                             help=" * The 'Draft' status is used when a user \
                                    is encoding a new and unconfirmed Invoice.\
                                    \n"
                                  " * The 'Pro-forma' when invoice is in \
                                  Pro-forma status,invoice does not have an \
                                  invoice number.\n"
                                  " * The 'Received' when invoice is receibed \
                                  from EDI\n"
                                  " * The 'Open' status is used when user \
                                  create invoice,a invoice number is \
                                  generated.Its in open status till user \
                                  does not pay invoice.\n"
                                  " * The 'Paid' status is set automatically \
                                  when the invoice is paid. Its related \
                                  journal entries may or may not be \
                                  reconciled.\n"
                                  " * The 'Cancelled' status is used when user \
                                  cancel invoice.")
    discount_ids = fields.One2many('account.discount', 'invoice_id',
                                   'Discounts')


class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
                 'product_id', 'invoice_id.partner_id',
                 'invoice_id.currency_id')
    def _compute_price(self):
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        if self.quantity != 0:
            if self.discount_ids:
                price = self.env['account.discount'].calculate_price(price)
            tax_line = self.invoice_line_tax_id
            taxes = tax_line.compute_all(price, self.quantity,
                                         product=self.product_id,
                                         partner=self.invoice_id.partner_id)
            self.price_subtotal = taxes['total']
            if self.invoice_id:
                self.price_subtotal = self.invoice_id.currency_id.\
                    round(self.price_subtotal)
            self.price_undiscounted = self.price_unit * self.quantity

    @api.one
    def _price_discounted(self):
        ctx = self._context.copy()
        price = 0.0
        if self.invoice_id.discount_ids:
            ctx['globals'] = [x.id for x in self.invoice_id.discount_ids]
            all_discounts = self.discount_ids + self.invoice_id.discount_ids
            all_percentage = True
            for discount in all_discounts:
                if not discount.percentage:
                    all_percentage = False

            if all_percentage:
                price = all_discounts.with_context(ctx)\
                    .calculate_price(self.price_unit * self.quantity,
                                     self, None)
            else:
                total = 0.0
                for line in self.invoice_id.invoice_line:
                    total += self.price_unit * self.quantity
                price = all_discounts.with_context(ctx)\
                    .calculate_price(total, self, total)
        self.price_subtotal_undiscounted = price

    # incluye unicamente descuentos de linea(es el que se muestra en
    # la vista
    discount_ids = fields.One2many('account.discount', 'invoice_line_id',
                                   'Discounts')

    price_subtotal = fields.Float(string='Amount',
                                  digits=dp.get_precision('Account'),
                                  store=True, readonly=True,
                                  compute='_compute_price')
    # precio sin ningun descuento
    price_undiscounted = fields.Float(string='Undiscounted',
                                      digits=dp.get_precision('Account'),
                                      store=False, readonly=True,
                                      compute='_compute_price')
    # precio que incluye los descuentos de linea y de factura
    price_subtotal_undiscounted = fields.Float(string='Price',
                                               digits=dp.get_precision('Account'),
                                               store=False, readonly=True,
                                               compute='_price_discounted')
    # precio que incluye los descuentos de linea y de factura
    global_discount = fields.Float('Global discount')
    global_charge = fields.Float('Global charge')

# class payment_type(models.Model):
#     """
#     Add generic fields
#     """
#     _inherit = 'payment.type'

#     edi_code = fields.Char('Edi Code', help="Code of payment type for EDI\
#                                              files")


class account_discount_type(models.Model):
    _name = "account.discount.type"
    _description = "Types of discounts/charges"

    code = fields.Char('Code', size=10, required=True)
    name = fields.Char('Name', size=64, required=True)


class account_discount(models.Model):
    _name = "account.discount"
    _description = "Discounts/Charges for invoices"

    # @api.multi
    # def name_get(self):
    #     import ipdb; ipdb.set_trace()
    #     res = [""]
    #     for discount in self:
    #         if discount.type_id:
    #             name = [discount.type_id.name]
    #         else:
    #             name = [discount.mode == 'A' and _('Discount') or _('Charge')]
    #         if discount.percentage:
    #             name.append(str(discount.percentage))
    #         elif discount.amount:
    #             name.append(str(discount.amount))
    #         res.append((discount.id, ", ".join(name)))

    # name = fields.Char('Name')

    @api.model
    def create(self, values):
        if 'amount' in values.keys() and values['amount'] > 0 or \
                'percentage' in values.keys() and values['percentage'] > 0:
            return super(account_discount, self).create(values)
        raise except_orm(_('Error'),
                         _('Discount need percentage or amount'))

    @api.one
    def write(self, values):
        valued = False
        for field in ['amount', 'percentage']:
            if field in values.keys() and values[field] > 0:
                valued = True
            elif field not in values.keys() and self[field] > 0:
                valued = True
        if valued:
            return super(account_discount, self).write(values)

        raise except_orm(_('Error'),
                         _('Discount need percentage or amount'))

    mode = fields.Selection([('A', 'Discount'), ('C', 'Charge')], 'Mode',
                            required=True)
    sequence = fields.Integer('Sequence')
    type_id = fields.Many2one('account.discount.type', 'Type')
    percentage = fields.Float('Percentage')
    amount = fields.Float('amount')
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    invoice_line_id = fields.Many2one('account.invoice.line', 'Line')

    def calculate_price(self, price_apply, line=None,
                        invoice_total_undiscounted=None):
        discount_obj = self.env['account.discount']
        global_discount_ids = self._context.get('globals', [])
        import ipdb; ipdb.set_trace()
        seq_list = [x.sequence for x in self]
        sequence_end = seq_list and max(seq_list) or 0
        price_aux = price_apply
        global_discount = 0
        global_charge = 0
        no_sequence = False
        if not sequence_end:
            sequence_end = 1
            no_sequence = True
        for index in range(sequence_end):
            discount_amount = 0.0
            search_context = [('id', 'in', [x.id for x in self])]
            if not no_sequence:
                search_context.append(('sequence', '=', index + 1))
            discount_seq_objs = discount_obj.search(search_context)
            for discount in discount_seq_objs:
                if no_sequence:
                    discount_amount = 0.0
                if discount.percentage > 0:
                    if discount.mode == u'A':
                        amount = price_aux - \
                            (price_aux * (1 - (discount.percentage / 100.0)))
                        discount_amount += amount
                    else:
                        amount = price_aux - \
                            (price_aux * (1 + (discount.percentage / 100.0)))
                        discount_amount += amount
                elif discount.amount > 0:
                    if discount.invoice_id:
                        if discount.mode == u'A':
                            discount_amount += (discount.amount / 100) * \
                                (line.price_undiscounted /
                                 (invoice_total_undiscounted / 100))
                        else:
                            discount_amount -= (discount.amount / 100) * \
                                (line.price_undiscounted /
                                 (invoice_total_undiscounted / 100))
                    else:
                        discount_amount += discount.mode == u'A' and \
                            discount.amount or -discount.amount
                if global_discount_ids:
                    if discount.id in global_discount_ids:
                        if discount.mode == u'A':
                            global_discount += discount_amount
                        else:
                            global_charge += discount_amount
                if no_sequence:
                    price_aux = price_aux - discount_amount

            if not no_sequence:
                price_aux = price_aux - discount_amount
            if line:
                if global_charge < 0:
                    global_charge = -global_charge
                line.write({'global_discount': global_discount,
                            'global_charge': global_charge})
        return price_aux
