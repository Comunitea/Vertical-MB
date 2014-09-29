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
# import time


class sale_order(osv.Model):
    _inherit = 'sale.order'

    _columns = {
        'route_id': fields.many2one('route', 'Transport Route', domain=[('state', '=',
                                                               'active')],
                                    readonly=True, states={'draft':
                                                           [('readonly',
                                                             False)],
                                                           'sent':
                                                           [('readonly',
                                                             False)]}),
    }

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        """
        When changing the partner the asociated route is filled, if any.
        """
        res = super(sale_order, self).onchange_partner_id(cr,
                                                          uid,
                                                          ids,
                                                          part=part,
                                                          context=context)
        partner_t = self.pool.get('res.partner')
        part = partner_t.browse(cr, uid, part, context=context)
        if not res['value'].get('route_id', []):
            if part.route_id:
                res['value']['route_id'] = part.route_id.id
        return res

    def _prepare_order_line_procurement(self, cr, uid, order, line,
                                        group_id=False, context=None):
        res = super(sale_order, self).\
            _prepare_order_line_procurement(cr, uid, order, line,
                                            group_id=group_id, context=context)
        res['route_id'] = order.route_id.id
        return res
