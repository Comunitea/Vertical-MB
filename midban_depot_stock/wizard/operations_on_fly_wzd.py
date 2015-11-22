# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicos Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
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
from openerp.addons.decimal_precision import decimal_precision as dp


class OperationsOnFlyWzd(models.TransientModel):

    _name = "operations.on.fly.wzd"

    @api.model
    def default_get(self, fields):
        res = super(OperationsOnFlyWzd, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return res
        wave_repp_obj = self.env['wave.report'].browse(active_ids[0])
        res.update({'product_id': wave_repp_obj.product_id.id})
        return res

    needed_qty = fields.Float('Needed Quantity',
                              digits=
                              dp.get_precision('Product Unit of Measure'),
                              required=True)
    product_id = fields.Many2one('product.product', 'Product')
    package_id = fields.Many2one('stock.quant.package', 'Package_id')

    @api.multi
    def create_operations(self):
        if self.env.context.get('active_ids', []):
            t_wr = self.env["wave.report"]
            report_obj = t_wr.browse(self.env.context['active_ids'][0])
            report_obj.create_operations_on_the_fly(report_obj.wave_id.id,
                                                    self.needed_qty,
                                                    self.package_id.id)
        return
