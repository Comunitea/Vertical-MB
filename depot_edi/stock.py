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


class stock_warehouse(models.Model):
    """
    Add EDI fields
    """
    _inherit = 'stock.warehouse'

    start_reception_hour = fields.Float('Start Reception')
    end_reception_hour = fields.Float('End Reception')


class stock_picking(models.Model):
    """
    Add EDI fields
    """
    _inherit = "stock.picking"

    num_dispatch_advice = fields.Char('Number dispatch advice', size=64)
    date_dispatch_advice = fields.Date('Date dispatch advice')
    supplier_pick_number = fields.Char('Number dispatch advice', size=64)
    order_date = fields.Date('Date of order', size=64)
    cantemb = fields.Integer('Palet quantity')
    document_id = fields.Many2one('edi.doc', 'EDI Document')
    name_doc = fields.Char('Ref', readonly=True, related='document_id.name')
    file_name_doc = fields.Char('File Name', readonly=True,
                                related='document_id.file_name')
    date_doc = fields.Datetime('Downloaded', readonly=True,
                               related='document_id.date')
    date_process_doc = fields.Datetime('Downloaded', readonly=True,
                                       related='document_id.date_process')
    state_doc = fields.Selection('State', readonly=True,
                                 related='document_id.state')
    message = fields.Text('Messagge', readonly=True,
                          related='document_id.message')
