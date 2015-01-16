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
from lxml import etree
from datetime import datetime
import shutil


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

    def make_backup(self, path, file_name):
        """

        """
        src_file = path
        dst_file = ''
        param_pool = self.env["ir.config_parameter"]
        param_obj = param_pool.search([('key', '=', 'edi.path.buckups')])
        year = time.strftime('%Y')
        month = time.strftime('%B')
        dst_file = os.path.join(str(param_obj.value + '/' + str(year) + '/' +
                                    month),
                                file_name)
        dir_month = str(param_obj.value + str(year) + '/' + month)
        dir_year = str(param_obj.value + str(year))
        if not os.path.exists(param_obj.value):
            os.mkdir(param_obj.value)
            os.mkdir(dir_year)
            os.mkdir(dir_month)
        elif not os.path.exists(dir_year):
            os.mkdir(dir_year)
            os.mkdir(dir_month)
        elif os.path.exists(dir_year) and not os.path.exists(dir_month):
            os.mkdir(dir_month)
        shutil.copy(src_file, dst_file)
        return log.info(_(u'The copy of the file to the backup was \
                         successful. Archivo %s' % file_name))

    def _parse_original_picking(self, file_path, root):
        """
        Read and process the DESADV file, returning the picking_obj
        The method maybe create some issues if some conditions are done.
        It return a picking obj or False
        """
        # Search for purchase order and the related picking
        purch_num = root.find('NUMPED').text
        purch_obj = self.env['purchase.order'].search([('name', '=',
                                                        purch_num)])
        if not purch_obj:
            log.error(_("Not found purchase order with number ") + purch_num)
            return False
        picking = self.env['stock.picking'].search([('purchase_id', '=',
                                                    purch_obj.id)])
        if not picking:
            log.error(_("Not found stock picking  for purchase: ") + purch_num)
            return False
        args = {
            'cantemb': root.find('./EMB/CANTEMB').text,
            'num_dispatch_advice': root.find('NUMDES').text,
            'date_dispatch_advice': root.find('FECDES').text,
        }
        if root.find('NUMALB') is not None:
            args['supplier_pick_number'] = root.find('NUMALB').text
        if root.find('FECPED') is not None:
            args['order_date'] = root.find('FECPED').text
        picking.write(args)

        # Process lines
        issue_lines = []
        for line in root.iter('LIN'):
            args_line = {}
            if self._check_picking_fields(file_path, line, 'line'):
                domain = [('ean13', '=', line.find('REFERENCIA').text)]
                products = self.env['product.template'].search(domain)
                # import ipdb; ipdb.set_trace()
                if not products:
                    refcli = line.find('REFCLI')
                    if refcli is not None:
                        refcli = refcli.text
                        domain = [('default_code', '=', refcli)]
                        products = self.env['product.template'].search(domain)
                        if not products:
                            log.error(_("Not found product with EAN: ") +
                                      line.find('REFERENCIA').text)
                            return False
            else:
                return False
        return picking

    def _check_fields(self, file_path, root, fields):
        """
        Check if a list of fields are int the DESADV file.
        """
        all_fields = True
        fields_not_found = []
        for field in fields:
            if root.find(field) is None:
                all_fields = False
                fields_not_found.append(field)
        if fields_not_found:
            fields_string = ""
            for field in fields_not_found:
                fields_string += field + ", "
            log.error(_(u'not found fields: ') + fields_string +
                      _(u'. in file: ') + file_path)
        return all_fields

    def _check_picking_fields(self, file_path, root, type_fields='file'):
        """
        Check fields of DESADV edi document, return True if correct False
        in other case.
        If type_fields == 'file' check the head tags (by default)
        else check the line tags.
        """
        fields_file = ['NUMDES', 'TIPO', 'FUNCION', 'FECDES', 'FECENVIO',
                       'NUMPED', './COMPRADOR/CODINTERLOCUTOR',
                       './RECEPTOR/CODINTERLOCUTOR', './EMB/CPS',
                       './EMB/CANTEMB']

        fields_line = ['REFERENCIA', 'CENVFAC', 'INSTMARCA', 'FECFABET',
                       'FECCADET', 'LOTE']
        fields = type_fields == 'file' and fields_file or fields_line
        return self._check_fields(file_path, root, fields)

    def parse_picking(self, file_path, doc):
        """
        This function parse the DESADV document in the call to
        _parse_original_picking function
        """
        print "PARSE DOC"
        xml = etree.parse(file_path)
        root = xml.getroot()
        function = root.find('FUNCION').text
        correct = True
        if not self._check_picking_fields(file_path, root):
            correct = False
        if function == '9' and correct:
            correct = self._parse_original_picking(file_path, root)
        if not correct:
            doc.write({'state': 'error'})
        else:
            doc.write({'state': 'imported', 'date_process': datetime.now()})
            correct.write({'document_id': doc.id})
            self.make_backup(file_path, doc.file_name)
            os.remove(file_path)
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
            file_path = path + os.sep + doc.file_name
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
