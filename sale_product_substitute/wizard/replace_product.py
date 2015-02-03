# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class replace_product(osv.TransientModel):
    _name = "replace.product"
    _description = ""
    DEC_PRECISION = dp.get_precision("Product Unit of Measure")
    _columns = {
        'product_id': fields.many2one('product.product',
                                      string="Product",
                                      required=True,
                                      ondelete='CASCADE'),
        'quantity': fields.float("Quantity",
                                 digits_compute=DEC_PRECISION,
                                 required=True),
        'product_uom': fields.many2one('product.uom',
                                       'Unit of Measure',
                                       required=True,
                                       ondelete='CASCADE'),
        'product_origin': fields.many2one('product.product',
                                          'Product orig'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        Fill the possibles fields with default values.
        """
        if context is None:
            context = {}
        res = super(replace_product, self).default_get(cr,
                                                       uid,
                                                       fields,
                                                       context)
        move_ids = context.get('active_ids', [])
        if not move_ids or len(move_ids) != 1:
            return res
        move = self.pool.get('stock.move').browse(cr,
                                                  uid,
                                                  move_ids[0],
                                                  context=context)
        if 'product_id' in fields:
            res.update(product_id=move.product_id.id)
        if 'quantity' in fields:
            res.update(quantity=move.state == 'assigned' and
                       move.product_qty or 0)
        if 'product_uom' in fields:
            res.update(product_uom=move.product_uom.id)
        if 'product_origin' in fields:
            res.update(product_origin=move.product_id.id)
        return res

    def replace_product(self, cr, uid, ids, context=None):
        """
        Substitute one product for another.
        """
        if context is None:
            context = {}
        line = context.get('active_ids', [])
        if not line or len(line) != 1:
            raise osv.except_osv(_('Error!'),  _('Cannot substitute the \
                                                  product because have not a \
                                                  related move.'))
        move = self.pool.get('stock.move')
        product = self.pool.get('product.product')
        wzd = self.browse(cr, uid, ids[0], context=context)
        form = move.browse(cr, uid, context['active_ids'][0])
        if wzd.product_id:
            products = []
            if form.product_id and wzd.product_id not in \
                    form.product_id.products_substitute_ids:
                products.append(wzd.product_id.id)
                if form.product_id.products_substitute_ids:
                    for sus in form.product_id.products_substitute_ids:
                        products.append(sus.id)
                vals = {'products_substitute_ids': [(6, 0, products)]}
                product.write(cr,
                              uid,
                              form.product_id.id,
                              vals)
            result = {'product_id': wzd.product_id.id,
                      'product_uom': wzd.product_uom.id,
                      'product_qty': wzd.quantity,
                      'prodlot_id': False,
                      'product_origin': form.product_id.id,
                      'qty_origin': form.product_qty,
                      'uom_origin': form.product_uom.id}
            move.write(cr,
                       uid,
                       context['active_ids'][0],
                       result)
        return {'type': 'ir.actions.act_window_close'}
