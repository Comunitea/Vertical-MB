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
from openerp import models, api, fields, tools
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from mako.template import Template
from mako.lookup import TemplateLookup
import os
import math


class export_edi_wzd(models.TransientModel):

    _name = "edi.export.wizard"

    service_id = fields.Many2one('edi', 'Service', required=True)

    @api.model
    def create_doc(self, doc_name, file_name, doc_type, obj=False):
        doc_objs = self.env['edi.doc'].search([('name', '=', doc_name)])
        doc_objs.unlink()
        f = open(file_name)
        values = {
            'name': doc_name,
            'file_name': file_name.split(os.sep)[-1],
            'state': 'export',
            'date': fields.Datetime.now(),
            'date_process': fields.Datetime.now(),
            'doc_type': doc_type.id,
            'message': f.read(),
            'service_id': self.service_id.id
        }
        f.close()
        file_obj = self.env['edi.doc'].create(values)
        if obj:
            obj.write({'document_id': file_obj.id})
        return file_obj

    @staticmethod
    def addons_path(path):
        report_module = path.split(os.path.sep)[0]
        for addons_path in tools.config['addons_path'].split(','):
            if os.path.lexists(addons_path+os.path.sep+report_module):
                return os.path.normpath(addons_path+os.path.sep+path)

    @api.model
    def _check_purchase_obj(self, obj):
        """
        Raise exceptions if purchase order obj or related objets have fields
        not correctly setted.
        """
        # Check supplier GLN
        if not obj.partner_id.gln:
            raise except_orm(_('Field error'),
                             _('The supplier has not gln'))
        # Check depot GLN
        if not obj.company_id.partner_id.gln and not \
                obj.company_id.partner_id.vat:
            raise except_orm(_('Field error'),
                             _('The depot has not gln or NIF'))
        # Check minimum planned date
        if not obj.minimum_planned_date:
            raise except_orm(_('Field error '),
                             _('Planned date field not \
                                configured!'))

        # Check Supplier address
        if not obj.partner_id.name or not \
                obj.partner_id.street or not obj.partner_id.city \
                or not obj.partner_id.zip:
            raise except_orm(_('Field error '),
                             _('The street configured for the \
                                supplier is not complete!'))
        # Check Depot address
        if not obj.company_id.partner_id.name or not \
                obj.company_id.partner_id.street or not \
                obj.company_id.partner_id.city or not obj.partner_id.zip:
            raise except_orm(_('Field error '),
                             _('The street configured for the \
                                depot is not complete!'))

        # Check Lines
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
            if not line.product_uom.code:
                    raise except_orm(_('Field error '),
                                     _('field  code of UdM not \
                                            configured'))
        return

    @api.model
    def _get_start_end_hours(self, obj):
        """
        Get and format the start hour and the end hour og warehouse related
        to the purchase
        """
        warehouse_start_hour = obj.warehouse_id.start_reception_hour
        warehouse_start_hour = \
            str(int(math.ceil((warehouse_start_hour -
                int(warehouse_start_hour)) * 60)))
        warehouse_start_hour = len(warehouse_start_hour) < 2 and \
            u'0' + warehouse_start_hour or warehouse_start_hour
        warehouse_start_hour = \
            str(int(obj.warehouse_id.start_reception_hour)) + \
            warehouse_start_hour
        warehouse_stop_hour = obj.warehouse_id.end_reception_hour
        warehouse_stop_hour = \
            str(int(math.ceil((warehouse_stop_hour -
                               int(warehouse_stop_hour)) * 60)))
        warehouse_stop_hour = \
            len(warehouse_stop_hour) < 2 and \
            u'0' + warehouse_stop_hour or warehouse_stop_hour
        warehouse_stop_hour = \
            str(int(obj.warehouse_id.end_reception_hour)) + \
            warehouse_stop_hour
        return warehouse_start_hour, warehouse_stop_hour

    @api.model
    def export_purchase_order(self):
        """
        Fills the template purchase_order_template to get ORDERS file
        """
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        doc_type_obj = self.env["edi.doc.type"]
        doc_type = doc_type_obj.search([("code", '=', "purchase_order")])[0]
        path = self[0].service_id.output_path
        templates_path = self.addons_path('depot_edi') + os.sep + 'wizard' + \
            os.sep + 'templates' + os.sep
        tmp_name = ''
        for obj in self.env[active_model].browse(active_ids):
            self._check_purchase_obj(obj)

            tmp_name = u'purchase_order_template.xml'
            filename = u'ORDERS_%s.xml' % (obj.name.replace(' ', u'')
                                           .replace('.', u''))
            mylookup = TemplateLookup(input_encoding='utf-8',
                                      output_encoding='utf-8',
                                      encoding_errors='replace')
            tmp = Template(filename=templates_path + tmp_name,
                           lookup=mylookup, default_filters=['decode.utf8'])

            # Convert warehouse hour to pass it to the template
            start, stop = self._get_start_end_hours(obj)
            start = start != u'000' and start or u''
            stop = stop != u'000' and stop or u''
            # This fill the template
            doc = tmp.render_unicode(o=obj, start=start,
                                     stop=stop).encode('utf-8', 'replace')
            # Creating the fisical file in the correct path
            file_name = path + os.sep + filename
            f = file(file_name, 'w')
            f.write(doc)
            f.close()
            # Creates the model EDI doc
            self.create_doc(filename, file_name, doc_type, obj=obj)

            # Post a notification message
            vals = {
                'body': _(u"The file has been created successfully correctly"),
                'model': 'purchase.order',
                'res_id': obj.id,
                'type': 'comment'
            }
            vals['body'] = vals['body'] + u' ' + file_name
            self.env['mail.message'].create(vals)

    @api.multi
    def export_files(self):
        """
        General function tu expor files from diferent modules like purchase
        order
        """
        active_model = self.env.context.get('active_model')
        if active_model == u'purchase.order':
            return self.export_purchase_order()
        return
