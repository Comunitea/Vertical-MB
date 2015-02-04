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
from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class stock_move(models.Model):

    _inherit = 'stock.move'

    q_note = fields.Many2one('qualitative.note', 'Qualitative Comment',
                             related="procurement_id.sale_line_id.q_note")
    det_note = fields.Char('Details', size=256,
                           related="procurement_id.sale_line_id.detail_note")

    @api.one
    def write(self, vals):
        """
        Overwrite in order to add th kg to the sale order line related when
        the sale type of product is ultrafresh
        """
        real_weight = vals.get('real_weight', False)
        # para arrastrar la ruta al albaran desde la venta
        if real_weight:
            t_uom = self.env['product.uom']
            real_weight = vals['real_weight']
            if real_weight and self.procurement_id and \
                    self.procurement_id.sale_line_id:
                if self.product_id.product_class == 'ultrafresh':
                    uom_obj = t_uom.search([('like_type', '=', 'kg')])
                    if uom_obj:
                        vals.update({
                            'product_uos': uom_obj[0].id,
                            'product_uos_qty': real_weight
                        })
                    else:
                        raise except_orm(_('Error'),
                                         _('Not founded kg uom, set the like \
                                            type field'))
                    self.procurement_id.sale_line_id.write(vals)
        res = super(stock_move, self).write(vals)
        return res
