# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Pexego Sistemas Informáticos All Rights Reserved
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
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


class EdiDocType(models.Model):

    _name = "edi.doc.type"

    code = fields.Char("Code", required=True)
    name = fields.Char("Name", required=True)
    description = fields.Text("Description")


class edi(models.Model):
    """
    Class for edi importations, the function run_scheduler is called by the
    import wizard.
    """
    _name = 'edi'
    _description = 'Provides general functions to impor edi files'

    name = fields.Char("Service name", required=True)
    path = fields.Char("System path", required=True)
    active = fields.Boolean("Active", default=True)
    backup_path = fields.Char("Backup path", required=True)
    output_path = fields.Char("Output path", required=True)
    doc_type_ids = fields.Many2many("edi.doc.type", string="Doc. types")

    @api.model
    def make_backup(self, path, file_name):
        for service in self:
            src_file = path
            dst_file = ''
            year = time.strftime('%Y')
            month = time.strftime('%B')
            dst_file = os.path.join(str(service.backup_path + '/' +
                                    str(year) + '/' + month), file_name)
            dir_month = str(service.backup_path + str(year) + '/' + month)
            dir_year = str(service.backup_path + str(year))
            if not os.path.exists(service.backup_path):
                os.mkdir(service.backup_path)
                os.mkdir(dir_year)
                os.mkdir(dir_month)
            elif not os.path.exists(dir_year):
                os.mkdir(dir_year)
                os.mkdir(dir_month)
            elif os.path.exists(dir_year) and not os.path.exists(dir_month):
                os.mkdir(dir_month)
            shutil.copy(src_file, dst_file)
            log.info(_(u'%s: The copy of the file to the backup was '
                        'successful. File %s' % (service.name, file_name)))

    @api.model
    def _check_fields(self, file_path, root, fields):
        """
        Check if a list of fields are int the DESADV or INVOIC file.
        Return False if someone of mandatory edi files is not in the EDI file
        @param fields: List of mandatory fields for the corresponding rdi file
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

# ****************************************************************************
# **************************** PICKINGS **************************************
# ****************************************************************************

    @api.model
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

    @api.model
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

    @api.model
    def _create_issue(self, reason_str, move=None, new_qty=0.0, picking=None):
        # Pedido de compra no servible / Imposible servir en plazo pactado
        type = self.env['issue.type'].search([('code', '=', 'type2')])
        type_id = type and type[0].id or False
        object = 'stock.picking'
        res_id = False
        product_lines = []
        origin = False
        flow = 'purchase.order,'
        edi_message = 'desadv2'
        if reason_str == 'reason6' and move:
            product_lines = [{
                'product_id': move.product_id.id,
                'product_qty': new_qty,
                'uom_id': move.product_uom.id,
            }]
            res_id = move.picking_id.id
            origin = move.purchase_line_id.order_id.name
            flow += str(move.purchase_line_id.order_id.id)
        elif reason_str == 'reason7' and picking:
            res_id = picking.id
            origin = picking.purchase_id.name
            flow += str(picking.purchase_id.id)
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
                               flow=flow,
                               product_ids=product_lines)
        return

    @api.model
    def _parse_picking_from_desadv(self, file_path, root):
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

    @api.model
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
            correct = self._parse_picking_from_desadv(file_path, root)
        if not correct:
            doc.write({'state': 'error'})
        else:
            doc.write({'state': 'imported', 'date_process': datetime.now()})
            correct.write({'document_id': doc.id})
            self.make_backup(file_path, doc.file_name)
            os.remove(file_path)
        return


# ****************************************************************************
# **************************** INVOICES **************************************
# ****************************************************************************
    @api.model
    def _check_invoice_fields(self, file_path, root, type_fields='head'):
        """
        Get a list of mandatory invoice edi files to check.
        """
        # node = self._context.get('node', False)
        fields_file = ['NUMFAC', 'NODO', 'FECHA', 'PEDIDO', 'ALBARAN',
                       './SEDESOC/CODINTERLOCUTOR',
                       './SEDESOC/NOMBRE', './SEDESOC/REG_MERCANTIL',
                       './SEDESOC/DIRECCION', './SEDESOC/POBLACION',
                       './SEDESOC/CP', './SEDESOC/NIF',
                       './SEDEPROV/CODINTERLOCUTOR',
                       './SEDEPROV/NOMBRE',
                       './SEDEPROV/REG_MERCANTIL', './SEDEPROV/DIRECCION',
                       './SEDEPROV/POBLACION', './SEDEPROV/CP',
                       './SEDEPROV/NIF',
                       './VENDEDOR/CODINTERLOCUTOR',
                       './COMPRADOR/CODINTERLOCUTOR',
                       './RECEPTOR/CODINTERLOCUTOR',
                       './CLIENTE/CODINTERLOCUTOR',
                       'DIVISA', './VENCFAC/VENCIMIENTO', 'SUMNETOS',
                       'BASIMPFA', 'TOTIMP', 'TOTAL', './IMPFAC/BASE',
                       './IMPFAC/TIPO',
                       './IMPFAC/TASA', './IMPFAC/IMPORTE'
                       ]
        fields_line = ['REFERENCIA', 'REFEAN', 'DESC', 'CFAC', 'NETO',
                       'PRECIOB', 'PRECION']

        # Check for atributtes
        if type_fields == 'line':
            fields = fields_line
            if 'NUMLIN' not in root.attrib.keys() or \
                root.find('DESC') is not None and \
                    'TIPART' not in root.find('DESC').attrib.keys():
                log.error(_(u'not found attribs: NUMLINEA or TIPART. in file:')
                          + file_path)
                return False
        else:
            fields = fields_file
        return self._check_fields(file_path, root, fields)

    @api.model
    def _create_invoice_from_picking(self, picking):
        """
        This function creates a invoice from a picking obj
        """
        invoice = False
        stock_inv_wzd = self.env['stock.invoice.onshipping']
        wzd_obj = stock_inv_wzd.with_context(active_ids=[picking.id]).\
            create({'invoice_date': time.strftime('%Y-%m-%d')})
        invoice_ids = wzd_obj.create_invoice()
        if invoice_ids:
            invoice = self.env['account.invoice'].browse(invoice_ids[0])
        return invoice

    @api.model
    def _get_related_invoice(self, root):
        """
        This function search the invoice related with PEDIDO edi tag,
        if not invoice founded we create one.
        """
        invoice = False
        t_po = self.env['purchase.order']
        t_pick = self.env['stock.picking']
        purch_num = root.find('PEDIDO').text
        purch_obj = t_po.search([('name', '=', purch_num)])
        if not purch_obj:
            log.error(_("Not found purchase order with number ") + purch_num)
            return False
        picking = t_pick.search([('purchase_id', '=', purch_obj.id)])
        if not picking:
            log.error(_("Not found stock picking  for purchase: ") + purch_num)
            return False
        if root.find('ALBARAN').text != picking.name:
            log.error(_("Diferent picking number: ") + purch_num)

        inv_objs = []
        inv_objs += [inv for inv in purch_obj.invoice_ids]
        invoice = inv_objs and inv_objs[0] or False
        if not invoice:
            invoice = self._create_invoice_from_picking(picking)
        if not invoice:
            log.error(_("Can not create a invoice for purchase: ") + purch_num)
            return False
        return invoice

    @api.model
    def _search_product(self, line):
        """
        Search a product by the ean13 field.
        """
        ref = line.find('REFERENCIA')
        product_obj = False
        if ref is not None:
            domain = [('ean13', '=', ref.text)]
            product_obj = self.env['product.product'].search(domain)
        return product_obj

    @api.model
    def generate_discount_statments(self, discount):
        disc_type_obj = self.env['account.discount.type']
        discount_search = []
        create = {}
        mode = discount.find('CALDTO')
        sequence = discount.find('SECUEN')
        type = discount.find('TIPO')
        percentage = discount.find('PORCEN')
        amount = discount.find('IMPDES')
        if type is not None and type.text == 'ABH':
            # si se trata de un rappel
            return (False, False)
        if mode is not None:
            discount_search.append(('mode', '=', mode.text))
            create['mode'] = mode.text
        if sequence is not None:
            discount_search.append(('sequence', '=', sequence.text))
            create['sequence'] = sequence.text
        if type is not None:
            disc_objs = disc_type_obj.search([('code', '=', type.text)])
            discount_search.append(('type_id', '=',
                                    disc_objs and disc_objs[0].id or False))
            create['type_id'] = disc_objs and disc_objs[0] or False
        if percentage is not None:
            discount_search.append(('percentage', '=', percentage.text))
            create['percentage'] = percentage.text
        if amount is not None:
            discount_search.append(('amount', '=', amount.text))
            create['amount'] = amount.text
        return (discount_search, create)

    @api.model
    def _search_taxes(self, product, line):
        tax_obj = self.env['account.tax']
        for tax in line.iter('IMPLFAC'):
            product_taxes = [x.id for x in product.supplier_taxes_id]
            domain = [
                ('code', '=', tax.find('TIPO').text),
                ('amount', '=', float(tax.find('TASA').text) / 100),
                ('id', 'in', product_taxes)
            ]
            tax_objs = tax_obj.search(domain)
            if not tax_objs:
                log.error(_(u'Impossible find tax with code ')
                          + tax.find('TIPO').text
                          + _(u' for product ') + product.name)
                return False
        return tax_objs

    @api.model
    def _create_invoice_issue(self, reason_str, inv_line=None,
                              invoice=None, new_qty=0.0, bad_product_id=None):
        # Error en recepción de factura
        type = self.env['issue.type'].search([('code', '=', 'type8')])
        type_id = type and type[0].id or False
        object = 'account.invoice'
        res_id = False
        product_lines = []
        origin = False
        flow = 'purchase.order,'
        edi_message = 'invoic'
        with_lin = ['reason82', 'reason83', 'reason84', 'reason87']
        no_lin = ['reason85', 'reason86', 'reason88']

        if reason_str == 'reason81' and bad_product_id:
            product_lines.append({
                'product_id': bad_product_id,
                'product_qty': new_qty,
                'uom_id': False,
                'reason_id': 'reason81'})
        if reason_str in with_lin and inv_line:
            res_id = inv_line.invoice_id.id
            origin = inv_line.purchase_line_id.order_id.name
            flow += str(inv_line.purchase_line_id.order_id.id)
            product_id = inv_line.product_id.id
            new_qty = new_qty and new_qty or inv_line.quantity
            if reason_str == 'reason81' and bad_product_id:
                product_id = bad_product_id
            product_lines = [{
                'product_id': product_id,
                'product_qty': new_qty,
                'uom_id': inv_line.uos_id.id,
            }]
        if reason_str in no_lin and invoice:
            res_id = invoice.id
            origin = invoice.invoice_line[0].purchase_line_id.order_id.name
            flow += str(invoice.invoice_line[0].purchase_line_id.order_id.id)
        # Create the issue with the type and reason and product lines correct
        issue_gen.create_issue(self._cr, self._uid, self._ids,
                               object, [res_id], reason_str, type_id=type_id,
                               edi_message=edi_message,
                               origin=origin,
                               flow=flow,
                               product_ids=product_lines)
        return

    @api.model
    def _parse_invoic_file(self, root, invoice):
        """
        Read an compare de invoic EDI file with the invoice obj founded
        previusly.
        If values in edi file are not in the invoice update the invoice.
        If diferencces between file and EDI log error and return False.
        Return the invoice if success
        """
        new_fields = {}
        gln_comp = root.find('./COMPRADOR/CODINTERLOCUTOR').text
        # Utilizar vendedor??
        gln_prov = root.find('./SEDEPROV/CODINTERLOCUTOR').text
        if gln_comp != invoice.company_id.partner_id.gln:
            log.error(_(u'Diferent buyer gln and partner of company gln'))
        if gln_prov != invoice.partner_id.gln:
            log.error(_(u'Different Supplier gln'))

        # Check NUMFAC with invoice_supplier_number
        if root.find('NUMFAC') is not None:
            numfac = root.find('NUMFAC').text
            if invoice.supplier_invoice_number:
                if invoice.supplier_invoice_number != numfac:
                    log.error(_(u'Diferent invoice supplier number'))
            else:
                new_fields['supplier_invoice_number'] = numfac

        # Check date descomentar y crear incidencia
        if root.find('FECHA') is not None:
            inv_date = root.find('FECHA').text
            st_dat = datetime.strptime(inv_date, "%Y%m%d").strftime("%Y-%m-%d")
            if invoice.date_invoice:
                if invoice.date_invoice != st_dat:
                    log.error(_(u'Diferent Invoice dates'))
            else:
                new_fields['date_invoice'] = st_dat

        # # Check payment type
        # no se si se corresponde con el pament term o que
        # if root.find('FPAG') is not None:
        #     fpag = root.find('FPAG').text
        #     ob_pay = self.env['payment.type'].search
        # ([('edi_code', '=', fpag)])

        #     ##
        #     if invoice.payment_type:
        #         if invoice.date_invoice != st_dat:
        #             log.error(_(u'Diferent Invoice dates'))
        #     else:
        #         new_fields['date_invoice'] = st_dat
        # Write new fields in the invoice

        # Check for commets,CONCATENAR
        if root.find('OBSFAC') is not None:
            obsfac = root.find('OBSFAC').text
            if invoice.comment:
                if obsfac != invoice.comment:
                    log.error(_(u'Diferent Comments in the invoice'))
            else:
                new_fields['comment'] = obsfac

        # Check for currency
        if root.find('DIVISA') is not None:
            divisa = root.find('DIVISA').text
            cur_obj = self.env['res.currency'].search([('name', '=', divisa)])
            if not cur_obj:
                log.error('Currency %s not founded in the system' % (divisa))
            if invoice.currency_id:
                if cur_obj.id != invoice.currency_id.id:
                    log.error('Different currencys')
            else:
                new_fields['currency_id'] = cur_obj.id

        # Check due date, GENERA INCIDENCIA,
        if root.find('./VENCFAC/VENCIMIENTO') is not None:
            ven_date = root.find('./VENCFAC/VENCIMIENTO').text
            vn_dat = datetime.strptime(ven_date, "%Y%m%d").strftime("%Y-%m-%d")
            if invoice.date_due:
                if invoice.date_invoice != vn_dat:
                    log.error(_(u'Diferent Due dates'))
            else:
                new_fields['date_due'] = vn_dat
            new_fields['date_due'] = vn_dat

        # Check for total
        totals_ok = True
        if root.find('BASEIMPFA') is not None:
            if invoice.amount_untaxed != root.find('BASEIMPFA').text:
                log.error(_(u'Diferent amount untaxed'))
                totals_ok = False
        if root.find('TOTIMP') is not None:
            if invoice.amount_tax != root.find('TOTIMP').text:
                log.error(_(u'Diferent amount tax'))
                totals_ok = False
        if root.find('TOTAL') is not None:
            if invoice.amount_total != root.find('TOTAL').text:
                log.error(_(u'Diferent amount Total'))
                totals_ok = False
        if not totals_ok:
            self._create_invoice_issue('reason88', invoice=invoice)
        # Check Taxes

        tax_ok = True
        for impfac in root.iter('IMPFAC'):
            tax_imp = impfac.find('IMPORTE').text
            base_imp = impfac.find('BASE').text
            found_base = False
            found_imp = False
            for tax_line in invoice.tax_line:
                if tax_line.base == base_imp:
                    found_base = True
                    break
                if tax_line.amount == tax_imp:
                    found_imp = True
                    break
            if not found_base:
                log.error(_('Differnt tax base %s not matching with invoice')
                          % base_imp)
                tax_ok = False
            if not found_imp:
                log.error(_('Differnt tax import %s not matching with invoice')
                          % tax_imp)
                tax_ok = False
        if not tax_ok:
            self._create_invoice_issue('reason85', invoice=invoice)
        # Process lines
        line_dicts = []  # for create issues
        lines_founded = []
        lines_invoice = invoice.invoice_line
        for line in root.iter('LINEA'):
            product_obj = self._search_product(line)
            # Buscamos producto, si no hay Devolvemos False
            if not product_obj:
                ref = line.find('REFERENCIA').text
                log.error(_('Not found reference % for product') % ref)
                return False
            product = product_obj[0]
            qty_tag = line.find('CFAC')
            # Buscamos linea
            domain = [('invoice_id', '=', invoice.id),
                      ('product_id', '=', product.id)]
            line_obj = self.env['account.invoice.line'].search(domain)
            # Si hay mas de una que coincidan las cantidades
            if len(line_obj) > 1:
                domain = [('invoice_id', '=', invoice.id),
                          ('product_id', '=', product.id)
                          ('quantity', '=', qty_tag.text)]
                line_obj = self.env['account.invoice.line'].search(domain)

            diff_dict = {'name': line.find('DESC').text}
            # Busqueda de impuestos, si no hay devolvemos False
            tax_objs = self._search_taxes(product, line)
            if not tax_objs:
                log.error(_('Not invoice line taxes matching with EDI file,'))
                return False
            # si existe la linea se busca si hay diferencias
            if line_obj:
                inv_line = line_obj[0]
                lines_founded.append(inv_line)
                # Check quantity
                if inv_line.quantity != float(qty_tag.text):
                    self._create_invoice_issue('reason82', inv_line=inv_line,
                                               new_qty=float(qty_tag.text))
                # Check price unit
                if inv_line.price_unit != float(line.find('PRECIOB').text):
                    self._create_invoice_issue('reason89', inv_line=inv_line)
                # line_tax_ids = [(4, x.id) for x in
                #                 inv_line.invoice_line_tax_id]
                # Check line taxes
                if inv_line.invoice_line_tax_id != tax_objs:
                    self._create_invoice_issue('reason83', inv_line=inv_line)

                # Check UOM
                if 'UMEDIDA' in qty_tag.attrib.keys():
                    domain = [('code', '=', qty_tag.attrib['UMEDIDA'])]
                    uom_obj = self.env['product.uom'].search(domain)
                    diff_dict['uos_id'] = uom_obj and uom_obj[0].id or False
                else:
                    diff_dict['uos_id'] = product.uom_id.id
                # Check Total
                if inv_line.price_subtotal != float(line.find('NETO').text):
                    self._create_invoice_issue('reason87', inv_line=inv_line)
                # Check discounts, launch issue if discount founded
                discount_issue = False
                # discounts_founded = []
                # diff_dict['discount_ids'] = []
                # disc_obj = self.env['account.discount']
                for discount in line.iter('DTOLFAC'):
                    discount_issue = True
                #     discount_search, create = self\
                #         .generate_discount_statments(discount)
                #     discount_search.append(('invoice_line_id', '=',
                #                             inv_line.id))
                #     discount_objs = disc_obj.search(discount_search)
                #     if not discount_objs:
                #         diff = True
                #         diff_dict['discount_ids'].append((0, 0, create))
                #     else:
                #         new_discount = \
                #             discount_objs[0].copy({'invoice_line_id': False})
                #         diff_dict['discount_ids'].append((4, new_discount.id))
                #         discounts_founded.append(discount_objs[0])
                # all_discounts = inv_line.discount_ids
                # discount_deleted = set(all_discounts) - set(discounts_founded)
                # if discount_deleted:
                #     diff = True
                if discount_issue:
                    self._create_invoice_issue('reason84', inv_line=inv_line)
            # SI no se encontro la linea
            else:
                self._create_invoice_issue('reason81', new_qty=qty_tag.text,
                                           bad_product_id=product.id)

            invoice.write(new_fields)
            line_dicts.append(diff_dict)

        line_objs = set(lines_invoice) - set(lines_founded)
        if line_objs:
            for line in line_objs:
                self._create_invoice_issue('reason81', inv_line=line)
        # invoice.signal_workflow('invoice_receives')
        return invoice

    @api.model
    def _parse_invoice_from_invoic(self, file_path, root):
        """
        This function return false if some error founded, return the invoice
        obj if success.
        """
        print "Parse full invoice"
        invoice = False
        xml = etree.parse(file_path)
        root = xml.getroot()
        nodo = root.find('NODO') is None and False or root.find('NODO').text
        if nodo == '380' and self.with_context(node=nodo).\
                _check_invoice_fields(file_path, root):
            invoice = self._get_related_invoice(root)
            invoice = self._parse_invoic_file(root, invoice)
        elif nodo == '381':  # Refund invoice
            # TODO FACTURA RECTIFICATIVA, nuffacsus LA RECTIFICADA?
            print "381"
        else:
            log.error(_(u'Not found corect NODO value \
                          in the INVOIC file ') + file_path)
        return invoice

    @api.model
    def parse_invoice(self, file_path, doc):
        """
        This function parse the INVOIC document in the call to
        _parse_original_picking function
        """
        print "PARSE INVOICE"
        xml = etree.parse(file_path)
        root = xml.getroot()
        invoice = self._parse_invoice_from_invoic(file_path, root)
        if not invoice:
            doc.write({'state': 'error'})
        else:
            doc.write({'state': 'imported', 'date_process': datetime.now()})
            invoice.write({'document_id': doc.id})
            self.make_backup(file_path, doc.file_name)
            os.remove(file_path)
        return

# ****************************************************************************
# **************************** GENERAL EDI ***********************************
# ****************************************************************************

    @api.model
    def process_files(self, path):
        """
        Search all edi docs in error or draft state and process it depending
        on the document type (picking, invoice)
        """
        for service in self:
            domain = [('state', 'in', ['draft', 'error'])]
            edi_docs = self.env['edi.doc'].search(domain)
            for doc in edi_docs:
                if doc.file_name not in os.listdir(path):
                    log.warning(_("%s: File not found in folder. File: %s")
                                % (service.name, doc.file_name))
                    continue
                log.set_errors("")
                process = False
                file_path = path + os.sep + doc.file_name
                if doc.doc_type.code == 'stock_picking':
                    service.parse_picking(file_path, doc)
                    process = True
                elif doc.doc_type.code == 'invoice':
                    service.parse_invoice(file_path, doc)
                    process = True
                if process:
                    doc.write({'errors': log.get_errors()})


    @api.model
    def _get_file_type(self, filename):
        doc_type_obj = self.env['edi.doc.type']
        if filename.startswith('INVOIC'):
            ftype = doc_type_obj.search([('code', '=', 'invoice')])[0]
        elif filename.startswith('DESADV'):
            ftype = doc_type_obj.search([('code', '=', 'stock_picking')])[0]
        else:
            ftype = False
        return ftype

    @api.model
    def _get_file_name(self, filename, type):
        if type.code in ('invoice', 'stock_picking'):
            return file_name.replace('.xml', '').split('_')[1]

    @api.model
    def run_scheduler(self, automatic=False, use_new_cursor=False):
        """
        This function will import all the files in the inmportation folder
        defined in the system parametres.
        The function also process the documents (DESADEV, INVOIC)
        """
        for service in self:
            path = service.path
            log.info(_(u'%s: Importing files') % service.name)
            files_downloaded = 0
            for file_name in os.listdir(path):
                type = self._get_file_type(file_name)
                name = self._get_file_name(file_name, type)

                # Search first edi documents in error state
                domain = [('name', '=', name), ('state', '=', 'error'),
                          ('doc_type', '=', type.id),
                          ('service_id', '=', service.id)]
                error_doc = self.env['edi.doc'].search(domain)

                if error_doc:
                    error_doc = error_doc[0]
                    f = codecs.open(path + os.sep + file_name, "r",
                                    "ISO-8859-1", 'ignore')
                    error_doc.write({'state': 'draft',
                                     'message': f.read()})
                    f.close()
                    files_downloaded += 1
                    log.info(u"%s: Updated previous error file %s "
                             % (service.name, file_name))

                # If no edi document founded we create it
                domain = [('file_name', '=', file_name),
                          ('doc_type', '=', type.id),
                          ('service_id', '=', service.id)]
                exist_doc = self.env['edi.doc'].search(domain)
                if not exist_doc:
                    f = codecs.open(path + os.sep + file_name, "r",
                                    "ISO-8859-1", 'ignore')
                    vals = {
                        'name': name,
                        'file_name': file_name,
                        'state': 'draft',
                        'date': fields.Datetime.now(),
                        'doc_type': type.id,
                        'message': f.read(),
                        'service_id': service.id
                    }
                    self.env['edi.doc'].create(vals)
                    f.close()
                    files_downloaded += 1
                    log.info(u"%s: Imported %s "
                             % (service.name, file_name))
                # Ignore in case of edi doc already exists
                else:
                    log.info(u"%s: Ignored %s, It's already in the system"
                             % (service.name, file_name))
            if files_downloaded:
                domain = [('state', 'in', ['draft', 'error']),
                          ('service_id', '=', service.id)]
                n_docs = self.env['edi.doc'].search_count(domain)
                log.info(u"%s: %s document(s) imported."
                         % (service.name, files_downloaded))
                log.info(u"%s: %s document(s) pending to process."
                         % (service.name, n_docs))
                service.process_files(path)


class edi_doc(models.Model):
    """
    Model for EDI document
    """
    _name = 'edi.doc'
    _description = 'EDI document'

    name = fields.Char('Ref.', size=255, required=True)
    file_name = fields.Char('File Name', size=255, required=True)
    doc_type = fields.Many2one("edi.doc.type", 'Document type')
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
    message = fields.Text('Message')
    errors = fields.Text('Errors')
    service_id = fields.Many2one("edi", "Service", required=True)
