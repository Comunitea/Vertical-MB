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
from openerp.osv import fields, osv
from openerp.tools.translate import _


class process_unregister_partner(osv.TransientModel):
    _name = "process.unregister.partner"
    _description = "Unregister partner and update the associated reasons"
    _columns = {
        'reason_id': fields.many2one('unregister.partner.reason',
                                     'Unregister Reason', required=True)
    }

    def unregister_partner(self, cr, uid, ids, context=None):
        """ Changes to unregistered state, register the unregister reason
        and desactive de product"""
        if context is None:
            context = {}
        partner_id = context and context.get('active_id', False)
        partner_obj = self.pool.get("res.partner").browse(cr, uid, partner_id)
        message = _("Unregistered")
        self.pool.get("res.partner")._update_history(cr, uid, ids, context, partner_obj, message)
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        partner_obj.write({'state2': 'unregistered', 'active': False,
                           'unregister_reason_id': wzd_obj.reason_id.id})
        return {'type': 'ir.actions.act_window_close'}
