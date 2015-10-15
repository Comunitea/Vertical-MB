# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Santi Argüeso <santi@comunitea.com>$
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


class ChangeLotPackageItems(models.TransientModel):
    _name = 'change.lot.package.items'

    change_lot_id = fields.Many2one('change.lot.package', 'Change Lot')
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    packed_qty = fields.Float('Quantity', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number',
                             domain="[('product_id', '=', product_id)]",
                             context="{'default_product_id':product_id}")
    #new_lot_id = fields.Many2one('stock.production.lot', 'New Lot/Serial Number')
    quant_id = fields.Many2one('stock.quant', 'Quant', readonly=True)


class ChangeLotPackage(models.TransientModel):

    _name = 'change.lot.package'

    package_id = fields.Many2one('stock.quant.package', 'Package')
    item_ids = fields.One2many('change.lot.package.items', 'change_lot_id', 'Items')

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(ChangeLotPackage, self).default_get(cr, uid, fields, context=context)
        package_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        if not package_ids or len(package_ids) != 1:
            return res
        assert active_model in ('stock.quant.package'), 'Bad context propagation'
        package_id, = package_ids
        package = self.pool.get('stock.quant.package').browse(cr, uid, package_id, context=context)
        items = []

        for quant in package.quant_ids:
            item = {
                'product_id': quant.product_id.id,
                'lot_id': quant.lot_id.id,
                'quant_id': quant.id,
                'packed_qty': quant.qty,
            }
            items.append(item)
        res.update(item_ids=items)
        return res

    @api.multi
    def change_lot(self):
        for item in self.item_ids:
            item.quant_id.lot_id = item.lot_id.id
