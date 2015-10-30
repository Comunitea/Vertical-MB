# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comuniteqa Servicios Tecnológicos
#    $Omar castiñeira Saavedraz$ <omar@comunitea.com>
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

from openerp import models, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _
import time
from reportlab.graphics.barcode import createBarcodeDrawing
import base64


class report_stock_tag_parser(models.AbstractModel):

    _name = 'report.midban_depot_stock.report_stock_tag'

    def barcode(self, type, value, width=600, height=100, humanreadable=0):
        width, height, humanreadable = int(width), int(height), bool(humanreadable)
        barcode_obj = createBarcodeDrawing(
            type, value=value, format='png', width=width, height=height,
            humanReadable = humanreadable
        )
        return base64.encodestring(barcode_obj.asString('png'))

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report_name = 'midban_depot_stock.report_stock_tag'
        report = report_obj._get_report_from_name(report_name)
        docs = []
        for inv in self.env[report.model].browse(self._ids):
            docs.append(inv)

        docargs = {
            'barcode': self.barcode,
            'docs': docs
        }
        return report_obj.render(report_name, docargs)
