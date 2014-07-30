# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier CFolmenero Fernández$ <javier@pexego.es>
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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv


class wzd_pack_operations(osv.TransientModel):
    """ Used to pack and set lots without using the barcode interface"""
    _name = "wzd.pack.operations"
    _columns = {
        'package_id': fields.many2one('stock.quant.package', 'Package'),
        'type': fields.selection([('box', 'Box'), ('mantle', 'Mantle'),
                                  ('palet', 'Palet')], 'Type'),
        'qty': fields.float('Quantity',
                            digits_compute=
                            dp.get_precision('Product Unit of Measure'),
                            required=True),
    }

    def create_operations(self, cr, uid, ids, context=None):
        """ Alternative way to barcode UI to create operations """
        print "--------------------------------------->Tranqui Tronco"
        return True
