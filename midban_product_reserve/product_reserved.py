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
from openerp import models, fields


class product_reserved(models.Model):
    _name = 'product.reserved'

    name = fields.Char('Name')
    created_date = fields.Date(string='Creation Date')
    expiry_date = fields.Date(string='Expiry Date')
    partner_id = fields.Many2one('res.partner')
    price_unit = fields.Float('Price unit')
    product_uom_id = fields.Many2one('product.uom', 'Unit',
                                     domain=[('like_type', 'in',
                                            ['units', 'boxes', 'kg'])]),
    invoice_type = fields.Selection([('promised', 'Promised'),
                                     ('invoiced', 'Invoiced')],
                                    'Invoice Type')
    reserved_qty = fields.Float('Reserved Qty')
    served_qty = fields.Float('Served Qty')
    pending_qty = fields.Float('Pending Qry')
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'),
                              ('calcelled', 'Cancelled'), ('Done', 'Done')],
                             'State', default='draft')
    comment = fields.Text('Comment')
    location_id = fields.Many2one('stock.location', 'Location')
