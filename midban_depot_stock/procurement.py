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
from openerp import api


class procurement_order(osv.osv):
    _inherit = "procurement.order"

    _columns = {
        'route_detail_id': fields.many2one('route.detail', 'Detail Route',
                                           readonly=True,
                                           domain=[('state', '=', 'active')],
                                           auto_join=True),
        # 'trans_route_id': fields.related('route_detail_id', 'route_id',
        #                                  string='Route',
        #                                  type="many2one",
        #                                  relation="route",
        #                                  store=True,
        #                                  readonly=True),
        'trans_route_id': fields.many2one('route', string="Route",
                                          readonly=True, auto_join=True),
    }

    # DESABILITAMOS MENSAJERÍA PARA PROCUREMENT ORDER
    @api.model
    def create(self, data):
        return super(procurement_order,
                    self.with_context(tracking_disable=True)).create(data)

    @api.multi
    def write(self, data):
        return super(procurement_order,
                     self.with_context(tracking_disable=True)).write(data)

    @api.model
    def _run_move_create(self, procurement):
        """
        Inherit to add the route_detail_id and transport route to the move
        """
        res = super(procurement_order, self)._run_move_create(procurement)
        if procurement.route_detail_id:
            res.update({'route_detail_id': procurement.route_detail_id.id,
                        'trans_route_id': procurement.trans_route_id.id})

        return res