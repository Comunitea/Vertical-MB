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
##############################################################################
from openerp.osv import osv, fields


class procurement_order(osv.osv):
    _inherit = "procurement.order"

    _columns = {
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                          domain=[('state', '=', 'active')]),
        # 'drop_code': fields.integer('Drop code', readonly=True),
    }

    def _run_move_create(self, cr, uid, procurement, context=None):
        """
        Overwrited to pass the product price kg to the move.
        """
        res = super(procurement_order, self)._run_move_create(cr, uid,
                                                              procurement,
                                                              context=context)
        res.update({'price_kg': procurement.product_id.price_kg})
        return res
