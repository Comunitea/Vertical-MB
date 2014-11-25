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
from openerp.tools.translate import _


class res_partner(osv.Model):
    _inherit = 'res.partner'
    _columns = {
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                          domain=[('state', '=', 'active')]),
    }

    @api.onchange('trans_route_id')
    @api.multi
    def onchange_route_id(self):
        """
        Check the delivery days of the customer and the route days.
        If no common days raise a warning
        raise a warning if some customer days are not in the transport route.
        """
        res = {}
        if not self.delivery_days_ids:
            warning = {
                'title': _('Warning!'),
                'message': _('There is no delivery days in this customer!'),
            }
        elif not self.trans_route_id.route_days_ids:
            warning = {
                'title': _('Warning!'),
                'message': _('There is no route days in the selected route!'),
            }
        else:
            partner_days = set(self.delivery_days_ids)
            route_days = set(self.trans_route_id.route_days_ids)
            common_days = partner_days & route_days
            if not common_days:
                warning = {
                    'title': _('Warning!'),
                    'message': _('Selected delivery days are not in the \
                                 transport Route!'),
                }
            else:
                diff_days = list(partner_days - common_days)
                diff_days = sorted(diff_days, key=lambda d: d.sequence)
                diff_days_str = ""
                for d in diff_days:
                    if not diff_days_str:
                        diff_days_str += d.name
                    else:
                        diff_days_str += "," + d.name
                if diff_days_str:
                    warning = {
                        'title': _('Warning!'),
                        'message': _('The days %s are not in the selected \
                                      transport route') % diff_days_str,
                    }
        res['warning'] = warning
        return res
