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
from openerp.osv import osv, fields
from openerp import api


class route(osv.Model):
    _name = 'tag'
    _description = 'Tags'
    _rec_name = 'product_id'
    _columns = {
        'product_id': fields.many2one('product.product', 'Product',
                                      required=True),
        'default_code': fields.char('Reference', size=128),
        'purchase_id': fields.many2one('purchase.order', 'Purchase order'),
        'package_id': fields.many2one('stock.quant.package', 'Package'),
        'date_order': fields.related('purchase_id', 'date_order',
                                     type="datetime", readonly=True,
                                     string="Date order"),
        'ean13': fields.char('EAN13', size=13),
        'type': fields.selection([('box', 'Box Tag'), ('palet', 'Palet Tag')],
                                 string="Type", required=True),
        'num_units': fields.float('Units'),
        'num_boxes': fields.float('Boxes'),
        'weight': fields.float('Weight'),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'removal_date': fields.date('Expiry Date'),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    _defaults = {
        'type': 'palet',
        'company_id': lambda self, cr, uid,
        c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Get default code and ean13"""
        self.default_code = self.product_id.default_code
        self.ean13 = self.product_id.ean13

    @api.onchange('lot_id')
    def onchange_lot_id(self):
        """ Get default code and ean13"""
        self.removal_date = self.lot_id.removal_date
