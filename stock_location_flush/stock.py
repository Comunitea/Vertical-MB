# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
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
from openerp import models, fields, api, exceptions, _
from datetime import datetime


class StockLocation(models.Model):

    _inherit = 'stock.location'

    location_flush_dest = fields.Many2one('stock.location', 'Flush location')

    @api.one
    def flush_location(self):
        import ipdb; ipdb.set_trace()
        if not self.location_flush_dest:
            raise exceptions.Warning(
                _('Location error'),
                _('Location %s not have flush destination') %
                self.complete_name)

        quants = self.env['stock.quant'].read_group(
            [('location_id', '=', self.id)],
            ['product_id', 'lot_id', 'qty'], ['product_id', 'lot_id'],
            lazy=False)
        if not quants:
            return

        wh = self.env['stock.location'].get_warehouse(self)
        type_search_dict = [('code', '=', 'internal')]
        if wh:
            type_search_dict.append(('warehouse_id', '=', wh))
        picking_type = self.env['stock.picking.type'].search(
            type_search_dict, limit=1, order="id")
        picking_vals = {
            'picking_type_id': picking_type.id,
            'date': datetime.now(),
            'origin': 'flush ' + self.complete_name + '->' +
            self.location_flush_dest.complete_name
        }
        picking_id = self.env['stock.picking'].create(picking_vals)
        for quant in quants:
            product = self.env['product.product'].browse(
                quant['product_id'] and quant['product_id'][0] or False)
            move_dict = {
                'name': product.name or '',
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uos': product.uom_id.id,
                'product_uom_qty': quant['qty'],
                'date': datetime.now(),
                'date_expected': datetime.now(),
                'location_id': self.id,
                'location_dest_id': self.location_flush_dest.id,
                'move_dest_id': False,
                'state': 'draft',
                'company_id': self.env.user.company_id.id,
                'picking_type_id': picking_type.id,
                'procurement_id': False,
                'origin': picking_id.origin,
                'invoice_state': 'none',
                'picking_id': picking_id.id
            }
            if quant['lot_id']:
                move_dict['restrict_lot_id'] = quant['lot_id'][0]
            self.env['stock.move'].create(move_dict).action_confirm()
        picking_id.action_assign()
        # picking_id.do_prepare_partial()
        # picking_id.do_transfer()

    @api.model
    def flush_location_cron(self):
        self.search([('location_flush_dest', '!=', False)]).flush_location()
