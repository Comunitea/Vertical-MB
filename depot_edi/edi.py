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
from openerp.exceptions import except_orm
from openerp.addons.midban_issue.issue_generator import issue_generator

issue_gen = issue_generator()
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

        fields_line = ['REFERENCIA', 'CENVFAC', 'FECFABET', 'FECCADET', 'LOTE']
        fields = type_fields == 'file' and fields_file or fields_line
        return self._check_fields(file_path, root, fields)

    def _create_operation_from_line(self, move, qty_serv, lot_id):
        """
        move is the matched move from the edi line with the erp
        This function creates a operation linked to the picking move
        """
        t_pack = self.env['stock.pack.operation']
        # Search or create lot
        vals = {
            'location_id': move.location_id.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'location_dest_id': move.location_dest_id.id,
            'picking_id': move.picking_id.id,
            'lot_id': lot_id,
            'product_qty': qty_serv,
        }
        return t_pack.create(vals)

    def _create_issue(self, reason_str, move=None, new_qty=0.0, picking=None):
        # Pedido de compra no servible / Imposible servir en plazo pactado
        type = self.env['issue.type'].search([('code', '=', 'type2')])
        type_id = type and type[0].id or False
        object = 'stock.picking'
        res_id = False
        product_lines = []
        origin = False
        flow = 'purchase.order'
        edi_message = 'desadv2'
        if reason_str == 'reason6' and move:
            product_lines = [{
                'product_id': move.product_id.id,
                'product_qty': new_qty,
                'uom_id': move.product_uom.id,
            }]
            res_id = move.picking_id.id
            origin = move.purchase_line_id.order_id.name
        elif reason_str == 'reason7' and picking:
            res_id = picking.id
            origin = picking.purchase_id.name
            for op in picking.pack_operation_ids:
                vals = {
                    'product_id': op.product_id.id,
                    'product_qty': op.product_qty,
                    'uom_id': op.product_uom_id and op.product_uom_id.id or
                    False,
                    'lot_id': op.lot_id and op.lot_id.id or False
                }
                product_lines.append(vals)
        # Create the issue with the type and reason and product lines correct
        issue_gen.create_issue(self._cr, self._uid, self._ids,
                               object, [res_id], reason_str, type_id=type_id,
                               edi_message=edi_message,
                               origin=origin,
                               product_ids=product_lines)
        return

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
            'supplier_pick_number': root.find('NUMDES').text,
        }
        if root.find('NUMALB') is not None:
            args['supplier_pick_number'] = root.find('NUMALB').text
        if root.find('FECPED') is not None:
            args['order_date'] = root.find('FECPED').text
        picking.write(args)
        # Create dict of moves by product, to match the move with the edi line
        moves_by_prod = {}
        for move in picking.move_lines:
            if move.product_id in moves_by_prod:
                raise except_orm(_('Error', _('Can not process moves with the\
                                               same product')))
            move_qty = move.product_uom_qty
            # the last float is the total qty served, processed in the lines
            moves_by_prod[move.product_id] = [move_qty, move, 0.0]
        # Process lines
        for line in root.iter('LIN'):
            if not self._check_picking_fields(file_path, line, 'line'):
                return False
            domain = [('ean13', '=', line.find('REFERENCIA').text)]
            product = self.env['product.product'].search(domain)
            # Check for product
            if not product:
                refcli = line.find('REFCLI')
                if refcli is not None:
                    refcli = refcli.text
                    domain = [('default_code', '=', refcli)]
                    product = self.env['product.product'].search(domain)
                    if not product:
                        log.error(_("Not found product with EAN: ") +
                                  line.find('REFERENCIA').text)
                        return False
            # Is product in the move lines?
            if product not in moves_by_prod:
                log.error(_("Not found product in the picking moves: ") +
                          product.name)
                return False
            # Check qtyis
            qty_serv = line.find('CENVFAC')
            try:
                qty_serv = int(qty_serv.text)
            except ValueError:
                log.error(_("The value of CENVFAC field is not an \
                            integer"))
                return False

            move = moves_by_prod[product][1]
            moves_by_prod[product][0] -= qty_serv

            # Search the lot and create it
            lot_num = line.find('LOTE').text
            fecfabet = line.find('FECFABET').text
            creation_date = datetime.strptime(fecfabet, '%Y%m%d')
            feccadet = line.find('FECCADET').text
            life_date = datetime.strptime(feccadet, '%Y%m%d')
            domain = [('name', '=', lot_num), ('product_id', '=', product.id)]
            lots_objs = self.env['stock.production.lot'].search(domain)
            if not lots_objs:
                vals = {
                    'name': lot_num,
                    'product_id': product.id,
                    'date': creation_date,
                    'life_date': life_date,
                }
                lot = self.env['stock.production.lot'].create(vals)
            else:
                lot = lots_objs[0]
            self._create_operation_from_line(move, qty_serv, lot.id)

        # Update the move qty if needed and launch issues
        for list_move in moves_by_prod.values():
            new_qty = list_move[0]
            orig_qty = list_move[1].product_uom_qty
            if new_qty > 0:
                self._create_issue('reason6', move=move, new_qty=new_qty)
                move.write({'product_uom_qty': orig_qty - new_qty})
            if list_move[0] < 0:
                # Create issue
                move.write({'product_qty': orig_qty + new_qty})

        # Check the min_date of picking to match with the edi date FECENT
        if root.find('FECENT') is not None:
            date_delivery_str = root.find('FECENT').text
            pick_date = datetime.strptime(picking.min_date,
                                          '%Y-%m-%d %H:%M:%S')
            if len(date_delivery_str) == 8:
                file_date = datetime.strptime(date_delivery_str, '%Y%m%d')
                pick_deliv_time = pick_date.strftime('%H%M%S')
                date_delivery_str = date_delivery_str + pick_deliv_time
            else:
                file_date = datetime.strptime(date_delivery_str,
                                              '%Y%m%d%H%M%S')

            if file_date.day != pick_date.day or file_date.month != \
                    pick_date.month or file_date.year != pick_date.year:
                self._create_issue('reason7', picking=picking)

        return picking

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
            # self.make_backup(file_path, doc.file_name)
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
