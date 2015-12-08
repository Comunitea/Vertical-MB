# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Informáticos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@comunitea.com>
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


class stock_invoice_onshipping(models.TransientModel):
    _inherit = 'stock.invoice.onshipping'

    group_fiscal = fields.Boolean('Group by parent partner', default = True)
    group = fields.Boolean('Group by partner', default = True)

    # @api.multi
    # def create_invoice(self):
    #     import ipdb; ipdb.set_trace()
    #
    #     if self.group_fiscal:
    #         ctx = self._context.copy()
    #         ctx['group_fiscal'] = True
    #
    #     else:
    #         res = super(stock_invoice_onshipping, self).create_invoice()
    #     return res

    def create_invoice(self, cr, uid, ids, context=None):

        context = dict(context or {})
        data = self.browse(cr, uid, ids[0], context=context)
        if data.group_fiscal:
            context['group_fiscal'] = True
        res = super(stock_invoice_onshipping, self).create_invoice(cr, uid,
                                                                   ids,
                                                                   context)
        return res

    # @api.onchange('group_fiscal')
    # def onchange_group_fiscal(self):
    #     if self.group_fiscal:
    #         self.group = True
    #
    @api.onchange('group')
    def onchange_group(self):
        if not self.group:
            self.group_fiscal = False
