# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
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
from openerp.addons.stock_account.wizard.stock_invoice_onshipping \
    import JOURNAL_TYPE_MAP
from openerp.tools.translate import _
from openerp.exceptions import except_orm


class ConfirmProcessDelivery(models.TransientModel):

    _name = 'confirm.process.delivery'

    @api.model
    def _get_journal(self):
        journal_obj = self.env['account.journal']
        journal_type = self._get_journal_type()
        journals = journal_obj.search([('type', '=', journal_type)],order='id')
        return journals and journals[0] or False

    @api.model
    def _get_journal_type(self):
        res_ids = self._context.get('active_ids', [])
        pick_obj = self.env['stock.picking']
        pickings = pick_obj.browse(res_ids)
        pick = pickings and pickings[0]
        if not pick or not pick.move_lines:
            return 'sale'
        type = pick.picking_type_id.code
        if type == 'incoming':
            usage = pick.move_lines[0].location_id.usage
        else:
            usage = pick.move_lines[0].location_dest_id.usage
        return JOURNAL_TYPE_MAP.get((type, usage), ['sale'])[0]

    journal_id = fields.Many2one('account.journal', 'Destination Journal',
                                 required=True, default=_get_journal)
    journal_type = fields.Selection(
        [('purchase_refund', 'Refund Purchase'),
         ('purchase', 'Create Supplier Invoice'),
         ('sale_refund', 'Refund Sale'), ('sale', 'Create Customer Invoice')],
        'Journal Type', readonly=True, default=_get_journal_type)
    group = fields.Boolean("Group by partner")
    invoice_date = fields.Date('Invoice Date')
    rendered = fields.Boolean('Rendered')

    @api.multi
    @api.onchange('journal_id')
    def onchange_journal_id(self):
        domain = {}
        value = {}
        active_id = self._context.get('active_id', False)
        if active_id:
            picking = self.env['stock.picking'].browse(active_id)
            type = picking.picking_type_id.code
            if type == 'incoming':
                usage = picking.move_lines[0].location_id.usage
            else:
                usage = picking.move_lines[0].location_dest_id.usage
            journal_types = JOURNAL_TYPE_MAP.get(
                (type, usage), ['sale', 'purchase', 'sale_refund',
                                'purchase_refund'])
            domain['journal_id'] = [('type', 'in', journal_types)]
        if self.journal_id:
            value['journal_type'] = self.journal_id.type
        return {'value': value, 'domain': domain}

    @api.one
    def create_invoice(self, pickings):
        pick_ids = [p.id for p in pickings if p.invoice_state == '2binvoiced'
                    and p.partner_id.invoice_method == 'a']
        invoice_wzd_vals = {
            'journal_id': self.journal_id.id,
            'journal_type': self.journal_type,
            'group': self.group,
            'invoice_date': self.invoice_date
        }
        invoice_wzd = self.env['stock.invoice.onshipping'].create(
            invoice_wzd_vals)
        invoice_ids = invoice_wzd.with_context(active_ids=pick_ids).create_invoice()
        invoices = self.env['account.invoice'].browse(invoice_ids)
        invoices.signal_workflow('invoice_open')

    # @api.multi
    # def confirm(self):
    #     picking_ids = self.env.context['active_ids']
    #     pickings = self.env['stock.picking'].browse(picking_ids)
    #     pickings_to_deliver = pickings.filtered(lambda r: r.state in
    #                                             ['assigned',
    #                                              'partially_available'])
    #     if not pickings_to_deliver:
    #         return
    #     res= pickings_to_deliver.do_prepare_partial()
    #     res = pickings_to_deliver.do_transfer()
    #     self.create_invoice(pickings_to_deliver)
    #     self.rendered = True
    #     return self.env['report'].get_action(
    #         pickings_to_deliver, 'stock_picking_batch.report_picking_batch')

    @api.multi
    def confirm(self):
        import ipdb; ipdb.set_trace()
        picking_ids = self.env.context['active_ids']
        pickings = self.env['stock.picking'].browse(picking_ids)
        picks_to_print = self.env['stock.picking']
        picks_to_process = self.env['stock.picking']
        for pick in pickings:
            if pick.state in ['assigned', 'partially_available']:
                picks_to_process += pick
            elif pick.state == 'done':
                picks_to_print += pick
            else:
                raise except_orm(_('Error'),
                                 _('Pick %s is in a invalid state: %s' % (pick.name, pick.state)))
        if picks_to_process:
            picks_to_process.do_prepare_partial()
            picks_to_process.do_transfer()
            if pick.invoice_state == '2binvoiced':
                self.create_invoice(picks_to_process)
        self.rendered = True
        all_picks = picks_to_print + picks_to_process
        return self.env['report'].get_action(
            all_picks, 'stock_picking_batch.report_picking_batch')
