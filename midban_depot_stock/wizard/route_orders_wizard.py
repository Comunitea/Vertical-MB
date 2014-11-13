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
#############################################################################
from openerp.osv import fields, osv
from openerp.tools.translate import _


class route_order_wizard(osv.TransientModel):
    _name = "route.order.wizard"
    _rec_name = "trans_route_id"
    _columns = {
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                    required=True,
                                    domain=[('state', '=', 'active')]),
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        order_t = self.pool.get(context['active_model'])

        record_id = context and context.get('active_id', False)
        order = order_t.browse(cr, uid, record_id, context=context)
        if order.state == 'done':
            msg = _("You cannot assign a route to a finished order")
            raise osv.except_osv(_('Warning!'), msg)
        return False

    def assign_route(self, cr, uid, ids, context=None):
        order_obj = self.pool.get(context['active_model'])
        if context is None:
            context = {}
        active_ids = context.get('active_ids', [])
        procurement_obj = self.pool.get('procurement.order')
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        obj = self.browse(cr, uid, ids[0], context=context)
        for order in order_obj.browse(cr, uid, active_ids, context):
            if context['active_model'] == "sale.order":
                p_ids = procurement_obj.search(cr, uid,
                                               [('sale_line_id.order_id', 'in',
                                                 context['active_ids'])],
                                               context=context)
                procurement_obj.write(cr, uid, p_ids,
                                      {'trans_route_id': obj.trans_route_id.id},
                                      context=context)
            elif context['active_model'] == "stock.picking":
                move_ids = move_obj.search(cr, uid, [('picking_id', 'in',
                                                      context['active_ids'])],
                                           context=context)
                pick_obj.write(cr, uid, context['active_ids'],
                               {'trans_route_id': obj.trans_route_id.id},
                               context=context)
                for move in move_obj.browse(cr, uid, move_ids,
                                            context=context):
                    move.procurement_id.write({'trans_route_id': obj.trans_route_id.id})
        return
