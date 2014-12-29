# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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


class StockReservation(models.Model):
    _inherit = 'stock.reservation'

    @api.one
    def _get_pending_qty(self):
        self.pending_qty = self.product_uom_qty - self.served_qty

    partner_id2 = fields.Many2one('res.partner', 'Customer', required=True,
                                  domain=[('customer', '=', True)])
    price_unit = fields.Float('Price Unit')
    served_qty = fields.Float('Served qty', readonly=True)
    pending_qty = fields.Float('Pending Qty', compute=_get_pending_qty,
                               readonly=True)
    invoice_method = fields.Selection([('2binvoiced', 'To be invoiced'),
                                       ('none', 'Agreement')])
    min_unit = fields.Selection('Min Unit', related="product_id.min_unit",
                                readonly=True)
    choose_unit = fields.Selection([('unit', 'Unit'),
                                    ('box', 'Box')], 'Selected Unit',
                                   default='unit')

    @api.multi
    def confirm_reserve(self):
        """ Confirm a reservation

        The reservation is done using the default UOM of the product.
        A date until which the product is reserved can be specified.
        """
        self.move_id.picking_id.action_done()
        return True

    @api.onchange('product_uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the uos of product
        """
        if self.min_unit == 'box' or \
                (self.min_unit == 'both' and self.choose_unit == 'box'):
            self.product_uom_qty = self.product_uos_qty * self.product_id.un_ca
        return

    @api.onchange('product_uom_qty')
    def product_uom_qty_onchange(self):
        """
        We change the uos of product
        """
        if self.min_unit == 'unit' or \
                (self.min_unit == 'both' and self.choose_unit == 'unit'):
            # self.product_uos_qty = self.product_id.un_ca != 0 and \
            #     self.product_uom_qty / self.un_ca or \
            #     self.product_uom_qty
            self.product_uos_qty = self.product_uom_qty
        return

    @api.onchange('product_id')
    def onchange_product_id(self):
        unit = self.env.ref('product.product_uom_unit')
        box = self.env.ref('midban_depot_stock.product_uom_box')
        if self.min_unit in ['unit', 'both']:
            self.choose_unit = 'unit'
            self.product_uom = unit.id
            self.product_uos = unit.id
        elif self.min_unit == 'box':
            self.choose_unit = 'box'
            self.product_uom = unit.id
            self.product_uos = box
