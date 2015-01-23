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
from openerp import models, fields


class StockWarehouse(models.Model):
    """
    Add generic fields
    """
    _inherit = 'account.tax'

    code = fields.Char('Code', help="Code of tax for EDI files")


class AccountInvoice(models.Model):
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
