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
from openerp.tools.translate import _
from wizard.edi_logging import logger
import os
import codecs
import time


log = logger("import_edi")


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

    def parse_picking(self, file_path, doc):
        print "PARSE DOC"
        return

    def process_files(self, path):
        """
        Search all edi docs in error or draft state and process it depending
        on the document type (picking, invoice)
        """
        domain = [('state', 'in', ['draft', 'error'])]
        edi_docs = self.env['edi.doc'].search(domain)
        for doc in edi_docs:
            if doc.file_name not in os.listdir(path):
                log.warning(_("File not found in folder. File: ") +
                            doc.file_name)
                continue
            log.set_errors("")
            file_path = path + doc.file_name
            if doc.doc_type == 'stock_picking':
                self.parse_picking(file_path, doc)
            # elif doc.type == 'invoice':
            #     self.parse_invoicefile_path, doc)
            doc.write({'errors': log.get_errors()})
        return

    def run_scheduler(self, automatic=False, use_new_cursor=False):
        """
        This function will import all the files in the inmportation folder
        defined in the system parametres.
        The function also process the documents (DESADEV, INVOIC)
        """
        domain = [('key', '=', 'edi.path.importation')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        path = param_obj.value  # Path for /out folder for edi files

        log.info(_(u'Importing files'))
        files_downloaded = 0
        for file_name in os.listdir(path):
            if file_name.startswith('INVOIC'):
                type = 'invoice'
            elif file_name.startswith('DESADV'):
                type = 'stock_picking'
            else:
                continue
            doc_type, name = file_name.replace('.xml', '').split('_')
            # Search first edi documents in error state
            domain = [('name', '=', name), ('state', '=', 'error')]
            error_doc = self.env['edi.doc'].search(domain)

            if error_doc:
                error_doc = error_doc[0]
                f = codecs.open(path + os.sep + file_name, "r", "ISO-8859-1",
                                'ignore')
                error_doc.write({'state': 'draft', 'message': f.read()})
                f.close()
                files_downloaded += 1
                log.info(u"Updated previus error file %s " % file_name)

            # If no edi document founded we create it
            domain = [('file_name', '=', file_name)]
            exist_doc = self.env['edi.doc'].search(domain)
            if not exist_doc:
                f = codecs.open(path + os.sep + file_name, "r", "ISO-8859-1",
                                'ignore')
                vals = {
                    'name': name,
                    'file_name': file_name,
                    'state': 'draft',
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'doc_type': type,
                    'message': f.read(),
                }
                self.env['edi.doc'].create(vals)
                f.close()
                files_downloaded += 1
                log.info(u"Imported %s " % file_name)
            # Ignore in case of edi doc already exists
            else:
                log.info(u"Ignored %s, It's already in the system" % file_name)
        domain = [('state', 'in', ['draft', 'error'])]
        n_docs = self.env['edi.doc'].search_count(domain)
        log.info(u"%s document(s) imported."
                 % files_downloaded)
        log.info(u"%s document(s) pending to process."
                 % n_docs)
        return self.process_files(path)
