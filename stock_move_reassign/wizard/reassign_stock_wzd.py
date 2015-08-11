# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicos Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
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


class ReassignStockWzd(models.Model):

    _name = "reassign.stock.wzd"

    line_ids = fields.One2many("reassign.stock.line.wzd", "wzd_id", "Lines",
                               domain=[("state", "=", "assigned")])

    @api.model
    def default_get(self, fields):
        res = super(ReassignStockWzd, self).default_get(fields)
        if self.env.context.get('active_ids', []):
            move_obj = self.env["stock.move"]
            move = move_obj.browse(self.env.context['active_ids'][0])
            assigned_moves = move_obj.search([('product_id', '=',
                                               move.product_id.id),
                                              ('state', '=', 'assigned'),
                                              ('location_id', '=',
                                               move.location_id.id)])
            res['line_ids'] = []
            for amove in assigned_moves:
                line = {
                    'move_id': amove.id,
                    'product_id': amove.product_id.id,
                    'product_qty': amove.product_uom_qty,
                    'uom_id': amove.product_uom.id,
                    'location_id': amove.location_id.id,
                    'partner_id': amove.partner_id.id,
                    'state': amove.state
                }
                res['line_ids'].append(line)
        return res

    @api.multi
    def unreserve(self):
        for wzd in self:
            for line in wzd.line_ids:
                line.move_id.do_unreserve()

        return True


class ReassignStockLineWzd(models.Model):

    _name = "reassign.stock.line.wzd"

    move_id = fields.Many2one("stock.move", "Move")
    product_id = fields.Many2one("product.product", "Product",
                                 readonly=True)
    product_qty = fields.Float("Quantity", readonly=True)
    uom_id = fields.Many2one("product.uom", "Uom", readonly=True)
    location_id = fields.Many2one("stock.location", "Location", readonly=True)
    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)
    state = fields.Selection([('draft', 'New'),('cancel', 'Cancelled'),
                              ('waiting', 'Waiting Another Move'),
                              ('confirmed', 'Waiting Availability'),
                              ('assigned', 'Available'),('done', 'Done')],
                              "State", readonly=True)
    wzd_id = fields.Many2one("reassign.stock.wzd", "Wzd")

