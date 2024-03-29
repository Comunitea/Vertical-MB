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


class ts_session_opening(osv.osv_memory):
    _name = 'ts.session.opening'

    _columns = {
        'name': fields.char('Name')
    }

    def open_ui(self, cr, uid, ids, context=None):
        """
        This method open TeleSale User Interface
        """
        context = context or {}
        # wzd_obj = self.browse(cr, uid, ids[0], context=context)
        # context['active_id'] = wzd_obj.pos_session_id.id
        return {
            'type' : 'ir.actions.act_url',
            'url':   '/ts/web/',
            'target': 'self',
        }
ts_session_opening()
