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

    @api.model
    def create(self, vals):
        """
        Overwrite to recalculate the readonly fields not passed to the vals.
        """
        if vals.get('product_id', False):
            unit = self.env.ref('product.product_uom_unit')
            box = self.env.ref('midban_depot_stock.product_uom_box')
            prod = self.env['product.product'].browse(vals['product_id'])
            min_unit = prod.min_unit
            choose2 = min_unit in ['unit', 'both'] and 'unit' or 'box'
            choose = vals.get('choose_unit', False) and vals['choose_unit'] \
                or choose2
            if min_unit == 'unit' or (min_unit == 'both' and choose == 'unit'):
                vals['product_uos_qty'] = vals.get('product_uom_qty', 0.0)
                vals['product_uos'] = unit.id
                vals['product_uom'] = unit.id
                vals['choose_unit'] = 'unit'
            elif min_unit == 'box' or (min_unit == 'both' and choose == 'box'):
                uos_qty = vals.get('product_uos_qty', 0.0)
                vals['product_uom_qty'] = uos_qty * prod.un_ca
                vals['product_uos'] = box.id
                vals['product_uom'] = unit.id
                vals['choose_unit'] = 'box'
        vals['name'] = '/'
        res = super(StockReservation, self).create(vals)
        return res

    @api.one
    def write(self, vals):
        """
        Overwrite to recalculate the product_uom_qty and product_uos_qty
        because of sometimes thei are readonly in the view and the onchange
        value is not in the vals dict
        """
        if vals.get('product_id', False):
            prod = self.env['product.product'].browse(vals['product_id'])
        else:
            prod = self.product_id

        if self.state != 'done':
            unit = self.env.ref('product.product_uom_unit')
            box = self.env.ref('midban_depot_stock.product_uom_box')
            min_unit = vals.get('min_unit', False) and vals['min_unit'] or \
                prod.min_unit
            choose2 = min_unit in ['unit', 'both'] and 'unit' or 'box'
            choose = vals.get('choose_unit', False) and vals['choose_unit'] \
                or choose2
            if min_unit == 'unit' or (min_unit == 'both' and choose == 'unit'):
                uom_qty = vals.get('product_uom_qty', 0.0) or \
                    self.product_uom_qty
                vals['product_uos_qty'] = uom_qty
                vals['product_uos'] = unit.id
                vals['product_uom'] = unit.id
                vals['choose_unit'] = 'unit'
            elif min_unit == 'box' or (min_unit == 'both' and choose == 'box'):
                uos_qty = vals.get('product_uos_qty', 0.0) or \
                    self.product_uos_qty
                vals['product_uom_qty'] = uos_qty * prod.un_ca
                vals['product_uos'] = box.id
                vals['product_uom'] = unit.id
                vals['choose_unit'] = 'box'
        res = super(StockReservation, self).write(vals)
        return res
