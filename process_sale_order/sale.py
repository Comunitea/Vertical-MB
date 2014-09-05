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
from openerp import models


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    # @api.onchange('product_id')
    # def product_id_change(self):
    #     import ipdb; ipdb.set_trace()
    #     return

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='',
                          partner_id=False, lang=False, update_tax=True,
                          date_order=False, packaging=False,
                          fiscal_position=False, flag=False, context=None):
        sup = super(sale_order_line, self)
        # import ipdb
        # ipdb.set_trace()
        res = sup.product_id_change(cr, uid, ids, pricelist, product,
                                    qty=0, uom=uom, qty_uos=qty_uos, uos=uos,
                                    name=name, partner_id=partner_id,
                                    lang=lang, update_tax=update_tax,
                                    date_order=date_order,
                                    packaging=packaging,
                                    fiscal_position=fiscal_position,
                                    flag=flag, context=context)
        return res
