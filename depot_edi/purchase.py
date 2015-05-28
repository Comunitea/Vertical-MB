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


class purchase_order(models.Model):
    """
    Add gln field for EDI
    """
    _inherit = 'purchase.order'

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
    message = fields.Text('Message', readonly=True,
                          related='document_id.message')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse',
                                   readonly=True,
                                   related='picking_type_id.warehouse_id')

    @api.multi
    def export_edi(self):
        ctx = {'active_model': 'purchase.order', 'active_ids': self._ids}
        edi_obj = self.env["edi"]
        edis = edi_obj.search([])
        for service in edis:
            for dtype in service.doc_type_ids:
                if dtype.code == "purchase_order":
                    wzd = self.env['edi.export.wizard'].with_context(ctx).\
                        create({'service_id': service.id})
                    wzd.export_files()
                    return
