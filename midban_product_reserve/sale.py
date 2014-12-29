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
from openerp import models, fields, api


class sale_order(models.Model):
    _inherit = 'sale.order'

    reserved_sale = fields.Boolean('Reserved Sale', readonly=True)

    # @api.model
    # def _prepare_order_line_procurement(self, order, line, group_id=False):
    #     res = super(sale_order, self).\
    #         _prepare_order_line_procurement(order, line, group_id=group_id)
    #     res.update({'route_id': line.route_id or False})
    #     return res
