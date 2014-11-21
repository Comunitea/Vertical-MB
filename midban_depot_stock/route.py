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


class route(osv.Model):
    _name = 'route'
    _description = 'Transport Route Model'
    _rec_name = 'code'
    _columns = {
        'code': fields.char('Code', size=32, required=True),
        'name': fields.char('Name', size=255),
        'vehicle_id': fields.many2one('stock.vehicle', 'Vehicle',
                                      required=True),
        'state': fields.selection([('draft', 'Draft'), ('active', 'Active')],
                                  string="State", readonly=True),
        'next_dc': fields.integer('Next Drop Code', readonly=True,
                                  required=True),
        'route_days_ids': fields.many2many('week.days',
                                           'routedays_week_days_rel',
                                           'route_id',
                                           'route_days_id',
                                           'Route Days'),
    }

    _defaults = {
        'state': 'draft',
        'next_dc': 1,
    }

    def set_active(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'active'}, context=context)

    def set_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def reset_drop_code(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'next_dc': '1'}, context=context)
