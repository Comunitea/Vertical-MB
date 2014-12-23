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
from openerp import netsvc


class process_deny_product(osv.TransientModel):
    """ You can see this wizard when you click on deny product button."""
    _name = "process.deny.product"
    _description = "Deny product and update the associated reasons"
    _columns = {
        'reason_id': fields.many2one('deny.product.reason',
                                     'Deny product Reason', required=True)
    }

    def deny_product(self, cr, uid, ids, context=None):
        """ Button method of deny wizard. Sets state to denied and desactive
            it for purchases.
            Also modify workflow to denied activity"""
        if context is None:
            context = {}
        product_id = context and context.get('active_id', False)
        product_obj = self.pool.get("product.template").browse(cr, uid,
                                                               product_id)
        message = _("Product Denied")
        self.pool.get("product.template")._update_history(cr, uid,
                                                          product_obj.id,
                                                          context, product_obj,
                                                          message)
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        product_obj.write({'state2': 'denied', 'active': False,
                           'purchase_ok': False,
                           'deny_reason_id': wzd_obj.reason_id.id})
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'product.template', product_id,
                                'deny', cr)
        return {'type': 'ir.actions.act_window_close'}
