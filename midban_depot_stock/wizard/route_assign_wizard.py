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
        pick_t = self.pool.get('stock.picking')
        if context is None:
            context = {}

        wzd_obj = self.browse(cr, uid, ids[0], context=context)

        domain = [
            ('state', 'not in', ['done', 'cancel']),
            ('min_date', '>=', wzd_obj.start_date),
            ('min_date', '<=', wzd_obj.end_date),
            ('picking_type_id.code', '=', 'outgoing'),
        ]
        model_ids = pick_t.search(cr, uid, domain, context=context)
        for pick in pick_t.browse(cr, uid, model_ids, context):
            if pick.partner_id.route_id:
                for move in pick.move_lines:
                    move.procurement_id.write({'route_id':
                                               pick.partner_id.route_id.id})
        return
