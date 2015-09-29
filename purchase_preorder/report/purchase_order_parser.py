# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Carlos Lombardía Rodríguez$ <carlos@comunitea.com>
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
from openerp import models, api, exceptions, _


class purchase_order_parser(models.AbstractModel):
    """
    """

    _name = 'report.purchase_preorder.replenishement_purchase_order'

    @api.multi
    def render_html(self, data=None):
        # import ipdb; ipdb.set_trace()

        report_obj = self.env['report']
        report_name = 'purchase_preorder.replenishement_purchase_order'
        report = report_obj._get_report_from_name(report_name)

        domain = [('order_id.create_date', '>=', data['start_date']),
                  ('order_id.create_date', '<=', data['end_date'])]
        line_objs = self.env['purchase.order.line'].search(domain)
        import ipdb; ipdb.set_trace()
        docargs = {
            'doc_ids': line_objs._ids,
            'doc_model': 'purchase_order',
            'docs': line_objs
        }
        return report_obj.render(report_name, docargs)
