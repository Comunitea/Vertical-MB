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
from openerp import models, api


class supplier_reception_parser(models.AbstractModel):
    """ Parser to get the supplier units conversions"""

    _name = 'report.midban_depot_stock.report_supplier_reception'

    def _get_unit_conversions(self, move):
        """
        Get the expected partition in palets, mantles and units ussing the
        measures of product sheet in suppliers page. (supplier measures).
        It say to us how the products are recived from the supplier
        """
        res = [0, 0, 0, 0]
        prod_obj = move.product_id
        move_qty = move.product_uom_qty

        un_ca = prod_obj.supplier_un_ca
        ca_ma = prod_obj.supplier_ca_ma
        ma_pa = prod_obj.supplier_ma_pa

        box_units = un_ca
        mantle_units = un_ca * ca_ma
        palet_units = un_ca * ca_ma * ma_pa

        remaining_qty = move_qty
        int_pal = 0
        int_man = 0
        int_box = 0
        int_units = 0

        while remaining_qty > 0:
            if remaining_qty >= palet_units:
                remaining_qty -= palet_units
                int_pal += 1
            elif remaining_qty >= mantle_units:
                remaining_qty -= mantle_units
                int_man += 1
            elif remaining_qty >= box_units:
                remaining_qty -= box_units
                int_box += 1
            else:
                int_units = remaining_qty
                remaining_qty = 0
        res = [int_pal, int_man, int_box, int_units]
        return res

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report_name = 'midban_depot_stock.report_supplier_reception'
        report = report_obj._get_report_from_name(report_name)
        docs = []
        conversions = {}
        for pick in self.env[report.model].browse(self._ids):
            docs.append(pick)
            for move in pick.move_lines:
                list_conv = self._get_unit_conversions(move)
                conversions[move] = list_conv
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': docs,
            'conversions': conversions,
        }
        return report_obj.render(report_name, docargs)
