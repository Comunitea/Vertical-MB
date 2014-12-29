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

    @api.model
    def _get_pending_qty(self):
        self.pending_qty = self.product_uom_qty - self.served_qty

    partner_id2 = fields.Many2one('res.partner', 'Customer', required=True,
                                  domain=[('customer', '=', True)])
    served_qty = fields.Float('Served qty', readonly=True)
    pending_qty = fields.Float('Pending Qty', compute=_get_pending_qty,
                                readonly=True)
    @api.multi
    def confirm_reserve(self):
        """ Confirm a reservation

        The reservation is done using the default UOM of the product.
        A date until which the product is reserved can be specified.
        """
        self.move_id.picking_id.action_done()
        return True