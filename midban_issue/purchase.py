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


class purchase_order(osv.Model):

    _inherit = 'purchase.order'

    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        t_issue = self.pool.get('issue')
        return {
            purchase_id: t_issue.search_count(cr, uid,
                                              [('res_model', '=',
                                                'purchase.order'),
                                               ('res_id', 'in', ids)],
                                              context=context)
            for purchase_id in ids
        }

    _columns = {
        'issue_count': fields.function(_issue_count, string='# Issues',
                                       type='integer'),
    }

    def issues_open(self, cr, uid, ids, context=None):
        """open issues related to purchases"""
        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference(cr, uid, 'midban_issue',
                                            'action_issue')
        action = self.pool.get(res[0]).read(cr, uid, res[1],
                                            context=context)
        domain = str([('res_model', '=', 'purchase.order'),
                      ('res_id', 'in', ids)])
        action['domain'] = domain
        return action
