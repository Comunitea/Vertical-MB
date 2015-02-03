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
from openerp.tools.translate import _


class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'

    def _get_action(self, cr, uid, context=None):
        """
        Add Delayed buy to procuremnt action.
        This type of procuremnts are resolved by buying products when the
        user launch the process cross dock wizard.
        """
        res = super(procurement_rule, self)._get_action(cr, uid,
                                                        context=context)
        return [('delayed_buy', _('Delayed Buy'))] + res


class procurement_order(osv.osv):
    _inherit = "procurement.order"
    _columns = {
        'buy_later': fields.boolean('Buy later', readonly=True),
    }

    def _run(self, cr, uid, procurement, context=None):
        """
        Overwrite to mark the procurement as buy later in order to find them
        later in the process cross dock wizard and make the purchase order
        when all the transport routes are well assigned.
        """
        if procurement.rule_id and procurement.rule_id.action == 'delayed_buy':
            # Mark procurement as to buy later.
            procurement.write({'buy_later': True}, context=context)
            return True
        res = super(procurement_order, self)._run(cr, uid, procurement,
                                                  context=context)
        return res
