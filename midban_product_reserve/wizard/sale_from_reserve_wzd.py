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


class sale_from_reserve_wzd(models.TransientModel):

    _name = "sale.from.reserve.wzd"
    _description = "Create sales from reserve"

    qty = fields.Float('Quantity', required=True)

    @api.multi
    def create_sale(self):
        import ipdb; ipdb.set_trace()
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not (active_model and active_ids) and \
                active_model != 'stock_reservation':
            return 
        reserve = self.env[active_model].browse(active_ids[0])
        new_served_qty = reserve.served_qty + self.qty
        reserve.write({'served_qty': new_served_qty})
        return