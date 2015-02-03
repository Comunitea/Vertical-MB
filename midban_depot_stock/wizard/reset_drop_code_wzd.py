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
from openerp.osv import osv


class reset_drop_code_wzd(osv.TransientModel):
    _name = "reset.drop.code.wzd"

    def reset_all_drop_codes(self, cr, uid, ids, context=None):
        """
        Reset all the transport routes drop codes.
        Field next_dc will be setted to 1
        """
        if context is None:
            context = {}
        t_route = self.pool.get("route")
        route_ids = t_route.search(cr, uid, [('state', '=', 'active')],
                                   context=context)
        if route_ids:
            t_route.write(cr, uid, route_ids, {'next_dc': 1}, context=context)
        return
