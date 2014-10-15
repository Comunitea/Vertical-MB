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


class stock_picking_in(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'operator': fields.boolean('Operator'),
        'frozen_operator': fields.boolean('Frozen Operator'),
        'location_mac_id': fields.many2one('stock.machine', 'Location Machine',
                                           domain=
                                           [('type', '=', 'retractil')]),
        'reposition_mac_id': fields.many2one('stock.machine',
                                             'Reposition Machine',
                                             domain=
                                             [('type', '=', 'retractil')]),
        'picking_mac_id': fields.many2one('stock.machine', 'Picking Machine',
                                          domain=
                                          ['|',
                                           ('type', '=', 'transpalet'),
                                           ('type', '=', 'prep_order')])
    }
