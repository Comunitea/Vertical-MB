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
import time
from openerp.tools.translate import _


class product_reserved(models.Model):
    _name = 'product.reserved'

    name = fields.Char('Name', required=True, default='/', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    min_unit = fields.Selection([('box', 'Only Boxes'),
                                ('unit', 'Only Unit'),
                                ('both', 'Both, units and boxes')],
                                string='Minimum Sale Unit',
                                required=True,
                                readonly=True,
                                related='product_id.min_unit',
                                help="Selecting both Units and boxes \
                                will add functionality to Telesale and \
                                Mobile App Sales (Android)")
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    creation_date = fields.Date(string='Creation Date', required=True,
                                default=time.strftime('%Y-%m-%d'))
    date_expiry = fields.Date(string='Expiry Date')
    price_unit = fields.Float('Price unit')
    product_uom_id = fields.Many2one('product.uom', 'Unit',
                                     domain=[('like_type', 'in',
                                            ['units', 'boxes', 'kg'])],
                                     required=True)
    invoice_type = fields.Selection([('promised', 'Promised'),
                                     ('invoiced', 'Invoiced')],
                                    string='Invoice Type', required=True,
                                    default='invoiced')
    reserved_qty = fields.Float('Reserved Qty')
    served_qty = fields.Float('Served Qty')
    pending_qty = fields.Float('Pending Qry', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'),
                              ('cancelled', 'Cancelled'), ('Done', 'Done')],
                             'State', default='draft')
    comment = fields.Text('Comment')
    location_id = fields.Many2one('stock.location', 'Location')

    # @api.model
    # def create(self, vals):
    #     box_uom = self.env['product.uom'].search([('like_type', '=', 'boxes')])
    #     un_uom = self.env['product.uom'].search([('like_type', '=', 'units')])
    #     if vals.get('name', '/') == '/':
    #         vals['name'] = self.env['ir.sequence'].get('pr.reserved') or '/'
    #     if vals.get('min_unit', False):
    #         vals['min_unit'] == self.env['ir.sequence'].get('pr.reserved') or '/'
    #     res = super(product_reserved, self).create(vals)
        return res

    @api.one
    def approve_reserve(self):
        self.state = 'approved'
        return

    @api.one
    def cancel_reserve(self):
        self.state = 'cancelled'
        return

    @api.one
    def back_draft(self):
        self.state = 'draft'
        return

    @api.one
    def finsh_reserve(self):
        self.state = 'done'
        return

    @api.onchange('min_unit')
    def onchange_min_unit(self):
        box_uom = self.env['product.uom'].search([('like_type', '=', 'boxes')])
        un_uom = self.env['product.uom'].search([('like_type', '=', 'units')])
        res = {}
        # if self.min_unit == 'box' or self.min_unit == 'both':
        if self.min_unit == 'box':
            if not len(box_uom):
                res['warning'] = {'title': _('Warning'),
                                  'message': _('Box unit does not exist.\
                You must configured one unit like boxes')}
            else:
                self.product_uom_id = box_uom.id

        else:  # Units
            if not len(un_uom):
                res['warning'] = {'title': _('Warning'),
                                  'message': _('Units unit does not exist.\
                You must configured one unit like units')}
            else:
                self.product_uom_id = un_uom.id
        return res
