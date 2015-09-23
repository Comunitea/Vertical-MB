# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
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
from openerp import models, fields, api

class print_purchase_report(models.TransientModel):

    _name = 'print.purchase.report.wzd'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    @api.multi
    def generate_print_purchase_report(self):
        # import ipdb; ipdb.set_trace()
        rep_name = 'purchase_preorder.replenishement_purchase_order'
        a = self.env["report"].get_action(self, rep_name)
        data_dic = {
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        a['data'] = data_dic
        return a
