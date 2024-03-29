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
from openerp.tools.translate import _
from openerp.exceptions import except_orm


class sale_from_reserve_wzd(models.TransientModel):

    _name = "sale.from.reserve.wzd"
    _description = "Create sales from reserve"
    _order = "id desc"

    @api.model
    def _get_default_uom(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not (active_model and active_ids) and \
                active_model != 'stock_reservation':
            return
        reserve = self.env[active_model].browse(active_ids[0])
        # res = reserve.choose_unit == 'unit' and reserve.product_uom.id or \
        #     reserve.product_uos.id
        res = reserve.product_uom.id or reserve.product_uos.id
        return res

    qty = fields.Float('Quantity', required=True)
    product_uom = fields.Many2one('product.uom', 'Uom', readonly=True,
                                  default=_get_default_uom)
    chanel = fields.Selection([('erp', 'ERP'), ('telesale', 'telesale'),
                               ('tablet', 'Tablet'),
                               ('other', 'Other'),
                               ('ecomerce', 'E-comerce')],
                              default='erp', readonly=True)

    @api.multi
    def _prepare_order_vals(self, reserve, chanel):
        order_policy = reserve.invoice_state == 'none' and 'picking' or \
            'invoiced_reserve'
        res = {
            'partner_id': reserve.partner_id2.id,
            'pricelist_id': reserve.partner_id2.property_product_pricelist.id,
            'partner_invoice_id': reserve.partner_id2.id,
            'partner_shipping_id': reserve.partner_id2.id,
            'reserved_sale': True,
            'order_policy': order_policy,
            'name': self.env["ir.sequence"].get('reserved.order') or '/',
            'chanel': chanel
        }
        return res

    @api.multi
    def _prepare_order_line_vals(self, reserve, so):
        xml_id = self.env.ref('midban_product_reserve.route_reserved_sales').id
        taxes_ids = reserve.product_id.taxes_id
        fpos = reserve.partner_id2.property_account_position
        tax_id = fpos and fpos.map_tax(taxes_ids) or [x.id for x in taxes_ids]
        uom_qty = uos_qty = self.qty
        if uom_qty > reserve.pending_qty:
                raise except_orm(_('Error!'),
                                 _('Only %s %s pending in the reserve') %
                                  (reserve.pending_qty,
                                   reserve.product_uom.name))
        res = {
            'order_id': so.id,
            'name': reserve.product_id.name,
            'product_id': reserve.product_id.id,
            'product_uom': reserve.product_uom.id,
            'product_uom_qty': uom_qty,
            'product_uos': reserve.product_uos.id,
            'product_uos_qty': uos_qty,
            'price_unit': reserve.price_unit,
            'route_id': xml_id,
            'tax_id': [(6, 0, tax_id)],
            # 'choose_unit': reserve.choose_unit,
        }
        return res

    @api.multi
    def create_sale(self):
        t_order = self.env['sale.order']
        t_line = self.env['sale.order.line']
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        chanel = self.chanel
        if not (active_model and active_ids) and \
                active_model != 'stock_reservation':
            raise except_orm(_('Error!'),
                             _('Imposible create reserved sale'))
        reserve = self.env[active_model].browse(active_ids[0])
        wzd_qty = self.qty
        new_served_qty = reserve.served_qty + wzd_qty
        vals = self._prepare_order_vals(reserve, chanel)
        so = t_order.create(vals)
        vals = self._prepare_order_line_vals(reserve, so)
        t_line.create(vals)
        reserve.write({'served_qty': new_served_qty})
        # Confirm the sale order
        so.action_button_confirm()
        # Open sale order in form view
        action_obj = self.env.ref('sale.action_orders')
        action = action_obj.read()[0]
        name_form = 'sale.view_order_form'
        view_id = self.env['ir.model.data'].xmlid_to_res_id(name_form)
        action.update(views=[(view_id, 'form')], res_id=so.id)
        return action
