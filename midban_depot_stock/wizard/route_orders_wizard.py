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
# from openerp.osv import fields, osv
# from openerp.tools.translate import _


# class route_order_wizard(osv.TransientModel):
#     _name = "route.order.wizard"
#     _rec_name = "trans_route_id"
#     _columns = {
#         'trans_route_id': fields.many2one('route', 'Transport Route',
#                                           domain=[('state', '=', 'active')]),
#     }

#     def view_init(self, cr, uid, fields_list, context=None):
#         if context is None:
#             context = {}
#         order_t = self.pool.get(context['active_model'])

#         record_id = context and context.get('active_id', False)
#         order = order_t.browse(cr, uid, record_id, context=context)
#         if order.state == 'done':
#             msg = _("You cannot assign a route to a finished order")
#             raise osv.except_osv(_('Warning!'), msg)
#         return False

#     def assign_route(self, cr, uid, ids, context=None):
#         """
#         Change route in one or several orders or picking, change a route in
#         orders must change route in related picking and vice verse.
#         We cange the route in the related procurements too.
#         """
#         order_obj = self.pool.get(context['active_model'])
#         if context is None:
#             context = {}
#         active_ids = context.get('active_ids', [])
#         t_proc = self.pool.get('procurement.order')
#         t_pick = self.pool.get('stock.picking')
#         order_obj = self.pool.get('sale.order')
#         t_route = self.pool.get('route')
#         obj = self.browse(cr, uid, ids[0], context=context)
#         new_route = obj.trans_route_id and obj.trans_route_id.id or False
#         next_dc = obj.trans_route_id and obj.trans_route_id.next_dc or 0
#         model = False
#         # FOR SALE ORDERS
#         if context['active_model'] == "sale.order":
#             model = order_obj
#         # FOR PICKINGS
#         elif context['active_model'] == "stock.picking":
#             model = t_pick
#         if model:
#             for model_obj in model.browse(cr, uid, active_ids, context):
#                 so_ids = set()
#                 group_id = False
#                 if model_obj.trans_route_id and new_route \
#                         and model_obj.trans_route_id.id == new_route:
#                     continue
#                 if 'sale_id' in model_obj._columns and model_obj.sale_id:
#                     so_ids.add(model_obj.sale_id.id)
#                     group_id = model_obj.group_id and \
#                         model_obj.group_id.id or False
#                 elif 'sale_id' not in model_obj._columns:
#                     so_ids.add(model_obj.id)
#                     group_id = model_obj.procurement_group_id and \
#                         model_obj.procurement_group_id.id or False
#                 if group_id:
#                     proc_ids = t_proc.search(cr, uid,
#                                              [('group_id', '=', group_id)],
#                                              context=context)
#                     if proc_ids:
#                         t_proc.write(cr, uid, proc_ids,
#                                      {'trans_route_id': new_route,
#                                       'drop_code': next_dc},
#                                      context=context)
#                         pick_ids = t_pick.search(cr, uid,
#                                                  [('group_id', '=', group_id)],
#                                                  context=context)
#                         if pick_ids:
#                             t_pick.write(cr, uid, pick_ids,
#                                          {'trans_route_id': new_route,
#                                           'drop_code': next_dc},
#                                          context=context)
#                 so_ids = list(so_ids)
#                 if so_ids:
#                     order_obj.write(cr, uid, so_ids,
#                                     {'trans_route_id': obj.trans_route_id.id},
#                                     context=context)
#                 if new_route:
#                     t_route.write(cr, uid, new_route, {'next_dc': next_dc + 1})
#         return
