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
        """
        Change route in one or several orders or picking, change a route in
        orders must change route in related picking and vice verse.
        We cange the route in the related procurements too.
        """
        order_obj = self.pool.get(context['active_model'])
        if context is None:
            context = {}
        active_ids = context.get('active_ids', [])
        t_proc = self.pool.get('procurement.order')
        move_obj = self.pool.get('stock.move')
        t_pick = self.pool.get('stock.picking')
        order_obj = self.pool.get('sale.order')
        obj = self.browse(cr, uid, ids[0], context=context)
        new_route = obj.trans_route_id and obj.trans_route_id.id or False
        # FOR SALE ORDERS
        if context['active_model'] == "sale.order":
            # Update orders
            order_obj.write(cr, uid, active_ids,
                            {'trans_route_id': new_route},
                            context=context)
            p_ids = t_proc.search(cr, uid,
                                  [('sale_line_id.order_id', 'in',
                                    active_ids)],
                                  context=context)
            # Update procurement route
            t_proc.write(cr, uid, p_ids,
                         {'trans_route_id': new_route},
                         context=context)
            # Update related pickings
            # pick_ids = []
            for so in order_obj.browse(cr, uid, active_ids, context):
                # pick_ids += [picking.id for picking in so.picking_ids]
                if so.group_id:
                    group_id = so.group_id.id
                    proc_ids = t_proc.search(cr, uid,
                                             [('group_id', '=', group_id)],
                                             context=context)
                    if proc_ids:
                        t_proc.write(cr, uid,
                                     {'trans_route_id': new_route},
                                     context=context)
                        pick_ids = t_pick.search(cr, uid,
                                                 [('group_id', '=', group_id)],
                                                 context=context)
                        if pick_ids:
                            t_pick.write(cr, uid,
                                         {'trans_route_id': new_route},
                                         context=context)
            # if pick_ids:
            #     t_pick.write(cr, uid, pick_ids,
            #                  {'trans_route_id': new_route},
            #                  context=context)
        # FOR PICKINGS
        elif context['active_model'] == "stock.picking":
            move_ids = move_obj.search(cr, uid, [('picking_id', 'in',
                                                  active_ids)],
                                       context=context)
            # Update pickings
            # t_pick.write(cr, uid, active_ids,
            #              {'trans_route_id': new_route},
            #              context=context)
             # Update procurement route
            for move in move_obj.browse(cr, uid, move_ids,
                                        context=context):
                move.procurement_id.write({'trans_route_id':
                                           new_route},
                                          context=context)
            # Update related orders
            # import ipdb; ipdb.set_trace()
            so_ids = set()
            for pick in t_pick.browse(cr, uid, active_ids, context):
                if pick.sale_id:
                    so_ids.add(pick.sale_id.id)
                if pick.group_id:
                    group_id = pick.group_id.id
                    proc_ids = t_proc.search(cr, uid,
                                             [('group_id', '=', group_id)],
                                             context=context)
                    if proc_ids:
                        t_proc.write(cr, uid, proc_ids,
                                     {'trans_route_id': new_route},
                                     context=context)
                        pick_ids = t_pick.search(cr, uid,
                                                 [('group_id', '=', group_id)],
                                                 context=context)
                        if pick_ids:
                            t_pick.write(cr, uid, pick_ids,
                                         {'trans_route_id': new_route},
                                         context=context)
            so_ids = list(so_ids)
            if so_ids:
                order_obj.write(cr, uid, so_ids,
                                {'trans_route_id': obj.trans_route_id.id},
                                context=context)
        return
