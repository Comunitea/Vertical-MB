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
from openerp import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_partner_to_invoice(self, cr, uid, picking, context=None):
        """
        """
        res = super(StockPicking, self).\
            _get_partner_to_invoice(cr, uid, picking, context=context)
        if context.get('group_fiscal'):
            res = picking.partner_id.commercial_partner_id.id
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_master_data(self, cr, uid, move, company, context=None):
        """
        """
        res = super(StockMove, self).\
            _get_master_data(cr, uid, move, company, context=context)
        if context.get('group_fiscal') and res:
            res = (move.picking_id.partner_id.commercial_partner_id, res[1],
                   res[2])
        return res
