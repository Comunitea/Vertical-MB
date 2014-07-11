# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
from openerp.osv import osv, fields
from midban_issue.issue_generator import issue_generator
issue_obj = issue_generator()


class stock_move(osv.Model):
    _inherit = 'stock.move'
    _columns = {
        'product_origin': fields.many2one('product.product', 'Product'),
        'qty_origin': fields.float('Qty. Origin'),
        'uom_origin': fields.many2one('product.uom', 'UdM')
    }


class stock_picking(osv.Model):
    _inherit = 'stock.picking'

    def action_move(self, cr, uid, ids, context=None):
        """Process the Stock Moves of the Picking

        This method is called by the workflow by the activity "move".
        Normally that happens when the signal button_done is received (button
        "Done" pressed on a Picking view).
        @return: True
        """
        res = super(stock_picking, self).action_move(cr,
                                                     uid,
                                                     ids,
                                                     context=context)
        issue = self.pool.get('issue')
        reason = self.pool.get('issue.reason')
        reas = False
        caused = False
        affected = False
        object = ''
        flow = ''
        for pick in self.browse(cr, uid, ids, context=context):
            for move in pick.move_lines:
                products = []
                if move.product_origin:
                    reas = reason.search(cr,
                                         uid,
                                         [('code', '=', 'reason10')])
                    if reas:
                        reas = reas[0]
                    domain = [('object', '=', 'stock.picking,' + str(pick.id)),
                              ('automatic', '=', True),
                              ('reason_id', '=', reas)]
                    issues = issue.search(cr, uid, domain)
                    if not issues:
                        products.append({'product_id': move.product_id.id,
                                         'product_qty': move.product_qty,
                                         'uom_id': move.product_uom.id})
                        products.append({'product_id': move.product_origin.id,
                                         'product_qty': -(move.qty_origin),
                                         'uom_id': move.uom_origin.id})
                        flow = move.picking_id and \
                            move.picking_id.sale_id and \
                            'sale.order,' + str(move.picking_id.sale_id.id) \
                            or False
                        object = "stock.picking," + str(move.picking_id and
                                 move.picking_id.id or False)
                        if move.picking_id and move.picking_id.partner_id:
                            affected = move.picking_id.partner_id.id
                        sale = move.picking_id and move.picking_id.sale_id \
                            or False
                        if sale and sale.shop_id and \
                                sale.shop_id.warehouse_id and \
                                sale.shop_id.warehouse_id.partner_id:
                            caused = sale.shop_id.warehouse_id.partner_id.id
                        elif move.picking_id.company_id:
                            caused = move.picking_id.company_id.partner_id.id
                        issue_obj.create_issue(cr,
                                               uid,
                                               ids,
                                               'stock.picking',
                                               move.picking_id and
                                               [move.picking_id.id] or
                                               False,
                                               'reason10',
                                               flow=flow,
                                               object=object,
                                               caused_partner_id=caused,
                                               affected_partner_id=affected,
                                               product_ids=products)
        return res
