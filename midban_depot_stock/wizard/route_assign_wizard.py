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
import time


class route_assign_wizard(osv.TransientModel):
    """
    For each picking put partners route id
    """
    _name = "route.assign.wizard"
    _columns = {
        'start_date': fields.datetime("Date Start", required=True),
        'end_date': fields.datetime("Date End", required=True),
    }
    _defaults = {
        'start_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def assign_route(self, cr, uid, ids, context=None):
        t_pick = self.pool.get('stock.picking')
        t_proc = self.pool.get('procurement.order')
        if context is None:
            context = {}

        wzd_obj = self.browse(cr, uid, ids[0], context=context)

        domain = [
            ('state', 'not in', ['done', 'cancel']),
            ('min_date', '>=', wzd_obj.start_date),
            ('min_date', '<=', wzd_obj.end_date),
            ('picking_type_id.code', 'in', ['outgoing', 'internal']),
            ('partner_id', '!=', False)
        ]
        model_ids = t_pick.search(cr, uid, domain, context=context)
        for pick in t_pick.browse(cr, uid, model_ids, context):
            if pick.partner_id.trans_route_id:
                pick.write({'trans_route_id':
                            pick.partner_id.trans_route_id.id})
                if pick.sale_id:
                    pick.sale_id.write({'trans_route_id':
                                       pick.partner_id.trans_route_id.id})
                for move in pick.move_lines:
                    move.procurement_id.write({
                        'trans_route_id':
                        pick.partner_id.trans_route_id.id})
                if pick.group_id:
                    group_id = pick.group_id.id
                    proc_ids = t_proc.search(cr, uid,
                                             [('group_id', '=', group_id)],
                                             context=context)
                    if proc_ids:
                        t_proc.write(cr, uid, proc_ids,
                                     {'trans_route_id':
                                      pick.partner_id.trans_route_id.id},
                                     context=context)
                        pick_ids = t_pick.search(cr, uid,
                                                 [('group_id', '=', group_id)],
                                                 context=context)
                        if pick_ids:
                            t_pick.write(cr, uid,
                                         {'trans_route_id':
                                          pick.partner_id.trans_route_id.id},
                                         context=context)
        return
