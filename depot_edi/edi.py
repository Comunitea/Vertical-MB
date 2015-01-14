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


class edi_doc(models.Model):
    """
    Model for EDI document
    """
    _name = 'edi.doc'
    _description = 'EDI document'

    name = fields.Char('Ref.', size=255, required=True)
    file_name = fields.Char('File Name', size=255, required=True)
    doc_type = fields.Selection([('purchase_order', 'Purchase'),
                                 ('stock_picking', 'Stock picking'),
                                 ('invoice', 'Invoice'),
                                 ('sale_order', 'Sale order')],
                                'Document type', select=1)
    date = fields.Datetime('Downloaded')
    date_process = fields.Datetime('Process')
    state = fields.Selection([('draft', 'Sin procesar'),
                              ('imported', 'Importado'),
                              ('export', 'Exportado'),
                              ('error', 'Con incidencias')],
                             'State', select=1)
    response_document_id = fields.Many2one('edi.doc',
                                           'Response Document')
    send_response = fields.Char('Response', size=255, select=1)
    send_date = fields.Datetime('Last Send Date', select=1)
    message = fields.Text('Messagge')
    errors = fields.Text('Errors')


class edi(models.Model):
    """
    Class for edi importations, the function run_scheduler is called by the
    import wizard.
    """
    _name = 'edi'
    _description = 'Provides general functions to impor edi files'

    def run_scheduler(self, automatic=False, use_new_cursor=False):
        print "VAMOS A IMPORTAR"
        return
