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


class sale_order_line(models.Model):
    """
    We must only do sale orders in units or boxes. Same products are only
    in units or only boxes, or maybe we can sale it in boxes and units.
    Field do_onchange is a workarround in order to control product_uos_qty and
    product_uom_qty onchange.
    """
    _inherit = "sale.order.line"

    do_onchange = fields.Integer('Do onchange')

    @api.onchange('product_uos_qty')
    def product_uos_qty_ochange(self):
        """
        We change the uos of product
        """
        # import ipdb; ipdb.set_trace()
        if self.do_onchange in [0, 2]:
            self.product_uom_qty = self.product_id.uos_coeff != 0 and \
                self.product_uos_qty / self.product_id.uos_coeff or \
                self.product_uom_qty
            self.do_onchange = self.do_onchange == 0 and -1 or -2
        else:
            if self.do_onchange == 3:
                self.do_onchange = 0
            else:
                self.do_onchange = 2
        return

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='',
                          partner_id=False, lang=False, update_tax=True,
                          date_order=False, packaging=False,
                          fiscal_position=False, flag=False,
                          do_onchange=4, context=None):
        """
        do_onchange controlls the calls to this function
        """
        # import ipdb; ipdb.set_trace()
        res = {'value': {'do_onchange': 0}}
        if do_onchange < 0:
            if do_onchange in [-1, -2]:
                res['value']['do_onchange'] = do_onchange == -1 and -3 or -4
            elif do_onchange in [-3, -4]:
                res['value']['do_onchange'] = do_onchange == -3 and 2 or 0
        else:
            sup = super(sale_order_line, self)
            res = sup.product_id_change(cr, uid, ids, pricelist, product,
                                        qty=qty, uom=uom, qty_uos=qty_uos,
                                        uos=uos, name=name,
                                        partner_id=partner_id,
                                        lang=lang, update_tax=update_tax,
                                        date_order=date_order,
                                        packaging=packaging,
                                        fiscal_position=fiscal_position,
                                        flag=flag, context=None)
            res['value']['do_onchange'] = do_onchange in [2, 4] and 3 or 1
        return res
