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
from openerp import models, fields, api


class ultrafresh_report_parser(models.AbstractModel):
    """ Parser to group sale ultrafresh products"""

    _name = 'report.midban_ultra_fresh.ultrafresh_purchase_report'

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report_name = 'midban_ultra_fresh.ultrafresh_purchase_report'
        report = report_obj._get_report_from_name(report_name)
        docs = []
        products = {}
        # import ipdb; ipdb.set_trace()
        for order in self.env[report.model].browse(self._ids):
            docs.append(order)
            for line in order.order_line:
                if line.product_id.sale_type == 'ultrafresh':
                    if line.product_id not in products:
                        products[line.product_id] = [line]
                    else:
                        products[line.product_id].append(line)
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': docs,
            'products': products,
        }
        # import ipdb; ipdb.set_trace()
        return report_obj.render(report_name, docargs)


class qualitative_note(models.Model):
    """ New model to get a qualitative comment un sale order lines"""
    _name = 'qualitative.note'
    _rec_name = 'code'

    name = fields.Char('name', required=True)
    code = fields.Char('code', required=True)


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    q_note = fields.Many2one('qualitative.note', 'Qualitative Comment')
