# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicos Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
#    $Javier Colmenero Fernández <javier@comunitea.com>$
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
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm


class ReassignStockWzd(models.TransientModel):

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
                    'picking_id': amove.picking_id.id,
                    'product_id': amove.product_id.id,
                    'product_qty': amove.product_uom_qty,
                    'uom_id': amove.product_uom.id,
                    'location_id': amove.location_id.id,
                    'partner_id': amove.partner_id.id,
                    'state': amove.state
                }
                res['line_ids'].append(line)
        return res

    def _reassign_quants_for_move(self, assigned_move, reassign_qty):
        t_move = self.env["stock.move"]
        t_quant = self.env["stock.quant"]
        import ipdb; ipdb.set_trace()
        to_assign_move = t_move.browse(self.env.context['active_ids'][0])
        for q in assigned_move.reserved_quant_ids:
            if reassign_qty:
                if reassign_qty >= q.qty:
                    q.reservation_id = to_assign_move.id
                    reassign_qty -= q.qty
                else:
                    new_q = t_quant._quant_split(q, reassign_qty)
                    new_q.reservation_id = to_assign_move.id
                    reassign_qty = 0
        return

    def _change_operations_for_move(self, assigned_move, reassign_qty):
        import ipdb; ipdb.set_trace()
        for link in assigned_move.linked_move_operation_ids:
            op = link.operation_id
            op_qty = op.product_qty if op.product_id else \
                op.package_id.packed_qty
            if op_qty > reassign_qty:
                prod = op.operation_product_id
                new_qty = op_qty - reassign_qty
                new_uos_qty = prod.uom_qty_to_uos_qty(new_qty, op.uos_id.id)
                vals = {
                    'product_id': prod.id,
                    'product_qty': new_qty,
                    'product_uom_id': prod.uom_id.id,
                    'lot_id': op.package_id.packed_lot_id.id,
                    'uos_qty': new_uos_qty,
                }
                op.write(vals)
                break
            else:
                op.unlink()
                reassign_qty -= op.qty
        return

    def _put_move_in_validated_picking(self):
        move_obj = self.env["stock.move"]
        wzd_move = move_obj.browse(self.env.context['active_ids'][0])
        import ipdb; ipdb.set_trace()
        return

    @api.multi
    def unreserve(self):
        self.ensure_one()
        wzd = self
        import ipdb; ipdb.set_trace()
        t_move = self.env["stock.move"]
        to_assign_move = t_move.browse(self.env.context['active_ids'][0])
        for line in wzd.line_ids:
            if not line.reassign_qty:
                continue
            if line.reassign_qty > line.product_qty:
                # line.move_id.do_unreserve()
                raise except_orm(_('Error'),
                                 _('Quantity to reassign greater than \
                                   unnasigned quantity for picking \
                                   %s' % line.picking_id.name))
            self._reassign_quants_for_move(line.move_id, line.reassign_qty)
            self._change_operations_for_move(line.move_id, line.reassign_qty)
            # self._create_operatio(line.move_id, line.reassign_qty)
            self._put_move_in_validated_picking()


        return True


class ReassignStockLineWzd(models.TransientModel):

    _name = "reassign.stock.line.wzd"

    move_id = fields.Many2one("stock.move", "Move")
    picking_id = fields.Many2one('stock.picking', 'Pick',
                                 readonly=True)
    product_id = fields.Many2one("product.product", "Product",
                                 readonly=True)
    product_qty = fields.Float("Quantity", readonly=True,
                               digits=dp.get_precision
                               ('Product Unit of Measure'))
    uom_id = fields.Many2one("product.uom", "Uom", readonly=True)
    location_id = fields.Many2one("stock.location", "Location", readonly=True)
    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)
    state = fields.Selection([('draft', 'New'),('cancel', 'Cancelled'),
                              ('waiting', 'Waiting Another Move'),
                              ('confirmed', 'Waiting Availability'),
                              ('assigned', 'Available'),('done', 'Done')],
                              "State", readonly=True)
    wzd_id = fields.Many2one("reassign.stock.wzd", "Wzd")
    reassign_qty = fields.Float('Qty to treassign',
                                digits=dp.get_precision
                                ('Product Unit of Measure'),
                                default=0.0)
