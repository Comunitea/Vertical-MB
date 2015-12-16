# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
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
from openerp.tools.float_utils import float_round
import openerp.addons.decimal_precision as dp


class manual_transfer_wzd(models.TransientModel):

    _name = 'several.procurement.product'

    @api.model
    def _get_default_warehouse(self):
        warehouse_id = False
        t_wh = self.env['stock.warehouse']
        wh_objs = t_wh.search([])
        if wh_objs:
            warehouse_id = wh_objs[len(wh_objs) - 1].id
        return warehouse_id

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse',
                                   required=True,
                                   default=_get_default_warehouse)
    item_product_ids = fields.One2many('item.product', 'wzd_id', 'Products')

    @api.multi
    def make_procurements(self):
        """
        Call default wizard of procurement product
        """
        self.ensure_one()
        wzd_proc = self.env['make.procurement']
        proc_ids = []
        for item in self.item_product_ids:
            vals = {
                'qty': item.qty,
                'product_id': item.product_id.id,
                'uom_id': item.uom_id.id,
                'warehouse_id': self.warehouse_id.id,
                'date_planned': item.date_planned
            }
            wzd_proc_obj = wzd_proc.create(vals)
            res = wzd_proc_obj.make_procurement()
            if res and res.get('res_id', False):
                proc_ids.append(res['res_id'])

        # Display the created procurements
        action_obj = self.env.ref('procurement.procurement_action')
        action = action_obj.read()[0]
        action['domain'] = str([('id', 'in', proc_ids)])
        action['context'] = {}
        return action


class ItemProduct(models.TransientModel):
    _name = 'item.product'

    wzd_id = fields.Many2one('several.procurement.product', 'Wizard')
    qty = fields.Float('Quantity', required=True, default=1.0)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    uom_id = fields.Many2one('product.uom', 'Unit of Measure',
                             related="product_id.uom_id", readonly=True)
    date_planned = fields.Date('Planned Date', required=True,
                               default=fields.Date.today())
    uos_qty = fields.Float('Quantity (S.U.)',
                           digits_compute=dp.
                           get_precision('Product Unit of Measure'),
                                         required=True)
    uos_id = fields.Many2one('product.uom', 'Second Unit',
                             required=True)

    @api.onchange('uos_id')
    def product_uos_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            # Change Uom Qty
            uos_id = self.uos_id.id
            uos_qty = self.uos_qty
            log_unit = product.get_uos_logistic_unit(uos_id)
            self.qty = product.uos_qty_to_uom_qty(uos_qty, uos_id)

    @api.onchange('uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            uos_id = self.uos_id.id
            uos_qty = float_round(self.uos_qty,
                              precision_rounding=self.uos_id.rounding,
                              rounding_method='UP')
            self.uos_qty = uos_qty
            self.qty = product.uos_qty_to_uom_qty(uos_qty, uos_id)

    @api.onchange('product_id')
    def product_id_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            product_udv_ids = product.get_sale_unit_ids()
            if product_udv_ids:
                self.uos_qty = 1.0
                self.uos_id = product_udv_ids[0]

