# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@pexego.es>
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
from openerp import models
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from mako.template import Template
from mako.lookup import TemplateLookup
import os
import time


class export_edi_wzd(models.TransientModel):
    _name = "edi.export.wizard"

    def create_doc(self, obj, file_name):
        active_model = self._context.get('active_model')
        if obj:
            name = doc_type = False
            if active_model == u'purchase.order':
                name = obj.name.replace(' ', '').replace('.', '')
                doc_type = 'purchase_order'
            elif active_model == u'account.invoice':
                name = obj.number.replace(' ', '').replace('/', '')
                doc_type = 'invoice'
            else:
                raise except_orm(_('Error'), _('The model is not a \
                                                   purchase order or invoice'))
            doc_objs = self.env['edi.doc'].search([('name', '=', name)])
            for doc in doc_objs:
                doc.unlink()
            f = open(file_name)
            values = {
                'name': name,
                'file_name': file_name.split('/')[-1],
                'status': 'export',
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'date_process': time.strftime('%Y-%m-%d %H:%M:%S'),
                'type': doc_type,
                'message': f.read(),
            }
            f.close()
            file_obj = self.env['edi.doc'].create(values)
            obj.write({'document_id': file_obj.id})

    def _check_purchase_obj(self, obj):
        """
        Raise exceptions if purchase order obj or related objets have fields
        not correctly setted.
        """
        if not obj.partner_id.gln:
                raise except_orm(_('Field error'),
                                 _('The supplier has not gln'))

        if not obj.minimum_planned_date:
            raise except_orm(_('Field error '),
                             _('Planned date field not \
                                    configured!'))
        if not obj.partner_id.name or not \
                obj.partner_id.street or not obj.partner_id.city \
                or not obj.partner_id.zip:
            raise except_orm(_('Field error '),
                             _('The street configured for the \
                                partner is not complete!'))

        for line in obj.order_line:
            if not line.product_id.ean13 and not line.product_id.ean14:
                raise except_orm(_('Field error'),
                                 _('The product not have \
                                       ean13/ean14. ') +
                                 line.product_id.name)
            if not line.product_id.default_code:
                raise except_orm(_('Field error '),
                                 _('field default_code of product \
                                       not configured'))
            # if not line.product_uom.code:
            #         raise except_orm(_('Field error '),
            #                          _('field  code of UdM not \
            #                                 configured'))
        return

    def export_purchase_order(self):
        print "EXPORTING PURCHASE ORDER"
        active_model = self._context.get('active_model')
        active_ids = self.env.context.get('active_ids')

        domain = [('key', '=', 'edi.path.exportation')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        path = param_obj.value
        domain = [('key', '=', 'edi.path.templates')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        templates_path = param_obj.value
        tmp_name = ''
        for obj in self.env[active_model].browse(active_ids):
            self._check_purchase_obj(obj)

            tmp_name = u'purchase_order_template.xml'
            file_name = u'%s%sORDERS_%s.xml' % (path, os.sep,
                                                obj.name.replace(' ', u'')
                                                .replace('.', u''))
            mylookup = TemplateLookup(input_encoding='utf-8',
                                      output_encoding='utf-8',
                                      encoding_errors='replace')
            tmp = Template(filename=templates_path + tmp_name,
                           lookup=mylookup, default_filters=['decode.utf8'])
            doc = tmp.render_unicode(o=obj).encode('utf-8', 'replace')
            f = file(file_name, 'w')
            f.write(doc)
            f.close()
            self.create_doc(obj, file_name)

            vals = {
                'body': _(u"The file has been created successfully correctly"),
                'model': 'purchase.order',
                'res_id': obj.id,
                'type': 'comment'
            }
            vals['body'] = vals['body'] + u' ' + file_name
            self.env['mail.message'].create(vals)

    def export_files(self):
        active_model = self.env.context.get('active_model')
        if active_model == u'purchase.order':
            return self.export_purchase_order()
        return
