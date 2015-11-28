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
from openerp.tools.float_utils import float_compare, float_round


class ReassignStockWzd(models.TransientModel):

    _name = "reassign.stock.wzd"

    @api.depends('line_ids')
    @api.one
    def _get_total_assigned(self):
        res = 0.0
        for l in self.line_ids:
            res += l.reassign_qty
        self.total_reassigned_qty= res
        self.pending_qty = self.unassigned_qty - res


    for_partner_id = fields.Many2one('res.partner', 'For Customer', readonly=True)
    unassigned_qty = fields.Float("Unassigned Quantity", readonly=True)
    pending_qty = fields.Float("Pending to assign", compute=_get_total_assigned, readonly=True)
    total_reassigned_qty = fields.Float("Total Reassigned", compute=_get_total_assigned, readonly=True)

    line_ids = fields.One2many("reassign.stock.line", "wizard_id", "Lines")

    @api.model
    def default_get(self, fields):
        res = super(ReassignStockWzd, self).default_get(fields)
        if self.env.context.get('active_ids', []):
            move_obj = self.env["stock.move"]
            move = move_obj.browse(self.env.context['active_ids'][0])
            domain = [
                ('id', '!=', move.id),
                ('product_id', '=', move.product_id.id),
                ('picking_id.wave_id', '=', False),
                '|',
                ('state', '=', 'assigned'),
                ('partially_available', '=', True),
                ('location_id', '=', move.location_id.id)]
            assigned_moves = move_obj.search(domain)
            res['line_ids'] = []
            res['for_partner_id'] = move.partner_id.id
            res['unassigned_qty'] = move.product_qty - move.reserved_availability
            for amove in assigned_moves:
                line = {
                    'move_id': amove.id,
                    'picking_id': amove.picking_id.id,
                    'product_id': amove.product_id.id,
                    'product_qty': amove.product_uom_qty,
                    'uom_id': amove.product_uom.id,
                    'assigned_qty': amove.reserved_availability,
                    'location_id': amove.location_id.id,
                    'partner_id': amove.partner_id.id,
                    'state': amove.state,
                    'reassign_qty': 0.00
                }
                res['line_ids'].append(line)
        return res

    def _reassign_quants_for_move(self, assigned_move, reassign_qty):
        t_move = self.env["stock.move"]
        t_quant = self.env["stock.quant"]
        to_assign_move = t_move.browse(self.env.context['active_ids'][0])
        rounding = to_assign_move.product_id.uom_id.rounding
        # reassign_qty = float_round(reassign_qty,
        #                           precision_rounding=0.01)
        # t = 0.0
        # import ipdb; ipdb.set_trace()

        for quant in assigned_move.reserved_quant_ids:
            # reassign_qty = float_round(reassign_qty,
            #                           precision_rounding=rounding)
            # quant_qty = float_round(quant.qty,

            quant_qty = quant.qty
            # print("Cant a reasignar %s" % reassign_qty)
            # print("Cant quant %s" %quant_qty)
            if reassign_qty > 0:
                if float_compare(reassign_qty, quant_qty,
                                 precision_rounding=rounding) >= 0:
                    quant.reservation_id = to_assign_move.id
                    reassign_qty -= quant_qty
                    # t += quant_qty
                    # print("Reasigno quant")

                else:
                    # import ipdb; ipdb.set_trace()
                    # print("Divido quant")
                    #
                    t_quant._quant_split(quant, reassign_qty)
                    quant.reservation_id = to_assign_move.id
                    # t += quant.qty
                    reassign_qty = 0
                    # print("Cantidad nuevo quant: %s" % quant.qty)
                # print("Total asignado: %s" % t)
                if float_compare(reassign_qty, 0,
                                 precision_rounding=rounding) == 0:
                    break
        return

    # def _change_operations_for_move(self, assigned_move, reassign_qty):
    #     for link in assigned_move.linked_move_operation_ids:
    #         op = link.operation_id
    #         op_qty = op.product_qty if op.product_id else \
    #             op.package_id.packed_qty
    #         if op_qty > reassign_qty:
    #             prod = op.operation_product_id
    #             new_qty = op_qty - reassign_qty
    #             new_uos_qty = prod.uom_qty_to_uos_qty(new_qty, op.uos_id.id)
    #             vals = {
    #                 'product_id': prod.id,
    #                 'product_qty': new_qty,
    #                 'product_uom_id': prod.uom_id.id,
    #                 'lot_id': op.package_id.packed_lot_id.id,
    #                 'uos_qty': new_uos_qty,
    #             }
    #             op.write(vals)
    #             break
    #         else:
    #             op.unlink()
    #             reassign_qty -= op.qty
    #     return

    def recalculate_state(self, move):
        reserved = move.reserved_availability
        uom_qty = move.product_uom_qty
        if not reserved:
            move.write({'state': 'confirmed', 'incomplete': True,
                        'partially_available': False})
        elif float_compare(reserved, uom_qty, precision_rounding=0.01) == 0:
            move.write({'state': 'assigned', 'incomplete': False,
                        'partially_available': False})
        elif float_compare(reserved, uom_qty, precision_rounding=0.01) < 0:
            move.write({'state': 'confirmed', 'partially_available': True,
                        'incomplete': True})
        else:
            raise except_orm(_('Error'),
                             _('reserved quantity (%s) greater than move \
                                quantity (%s)' % (reserved, uom_qty)))
        return

    @api.multi
    def unreserve(self):
        # self.ensure_one()
        # wzd = self
        t_move = self.env["stock.move"]
        to_assign_move = t_move.browse(self.env.context['active_ids'][0])
        for wzd in self:
            for line in wzd.line_ids:
                if not line.reassign_qty:
                    continue
                if line.reassign_qty > line.assigned_qty:
                    # line.move_id.do_unreserve()
                    raise except_orm(_('Error'),
                                     _('Quantity to reassign greater than \
                                       unnasigned quantity for picking \
                                       %s' % line.picking_id.name))
                self._reassign_quants_for_move(line.move_id, line.reassign_qty)
                # import ipdb; ipdb.set_trace()
                # line.move_id.recalculate_move_state()
                # to_assign_move.recalculate_move_state()
                self.recalculate_state(line.move_id)
                self.recalculate_state(to_assign_move)
                # self._change_operations_for_move(line.move_id, line.reassign_qty)
                line.move_id.picking_id.delete_picking_package_operations()
                line.move_id.picking_id.do_prepare_partial()
                to_assign_move.picking_id.delete_picking_package_operations()
                to_assign_move.picking_id.do_prepare_partial()
        return True


class ReassignStockLineWzd(models.TransientModel):

    _name = "reassign.stock.line"

    wizard_id = fields.Many2one('reassign.stock.wzd', "Wzd")
    move_id = fields.Many2one("stock.move", "Move", readonly=True)
    picking_id = fields.Many2one('stock.picking', 'Pick',
                                 readonly=True)
    product_id = fields.Many2one("product.product", "Product",
                                 readonly=True)
    # product_qty = fields.Float("Quantity", readonly=True,
    #                            digits=dp.get_precision
    #                            ('Product Unit of Measure'))
    product_qty = fields.Float("Quantity", readonly=True)
    uom_id = fields.Many2one("product.uom", "Uom", readonly=True)
    location_id = fields.Many2one("stock.location", "Location", readonly=True)
    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)
    state = fields.Selection([('draft', 'New'),('cancel', 'Cancelled'),
                              ('waiting', 'Waiting Another Move'),
                              ('confirmed', 'Waiting Availability'),
                              ('assigned', 'Available'),('done', 'Done')],
                              "State", readonly=True)
    # reassign_qty = fields.Float('Qty to treassign',
    #                             digits=dp.get_precision
    #                             ('Product Unit of Measure'),
    #                             default=0.0)
    # assigned_qty = fields.Float('Qty to treassign',
    #                             digits=dp.get_precision
    #                             ('Product Unit of Measure'),
    #                             default=0.0)
    assigned_qty = fields.Float('Qty assigned', readonly=True)
    reassign_qty = fields.Float('Qty to assign')

