# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunit All Rights Reserved
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
from openerp import models, fields, api


class crm_phonecall(models.Model):
    _inherit = 'crm.phonecall'

    detail_id = fields.Many2one('route.detail', 'Route detail', readonly=True,
                                ondelete="cascade")
    result = fields.Selection([('sale_done', 'Sale done'),
                               ('not_done', 'Not Done'),
                               ('not_responding', 'Not responding'),
                               ('comunicate', 'Comunicate'),
                               ('call_no_order', 'Call without order'),
                               ('call_other_moment', 'Call other moment'),
                               ('call_no_done', 'Call not done')],
                              string="Call result",
                              default="not_done")

    @api.one
    def write(self, vals):
        """
        Modify the state of the call based on the result visit
        """
        if vals.get('result', False):
            if vals['result'] in ['sale_done', 'call_no_order']:
                vals['state'] = 'done'
            elif vals['result'] in ['comunicate', 'not_responding', 'not_done']:
                vals['state'] = 'pending'
            elif vals['result'] in ['call_other_day', 'call_other_moment']:
                vals['state'] = 'open'
            elif vals['result'] in ['call_no_done']:
                vals['state'] = 'cancel'
        res = super(crm_phonecall, self).write(vals)
        return res
