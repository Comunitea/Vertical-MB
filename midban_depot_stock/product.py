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
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class product_template(osv.Model):
    """
    Adding field picking location
    """
    _inherit = "product.template"

    _columns = {
        'picking_location_id': fields.many2one('stock.location',
                                               'Location Picking',
                                               domain=[('usage', '=',
                                                        'internal')]),
        'volume': fields.float('Volume', help="The volume in m3.",
                               digits_compute=
                               dp.get_precision('Product Volume')),

    }
    _sql_constraints = [
        ('location_id_uniq', 'unique(picking_location_id)',
         _("Field Location picking is already setted"))
    ]


class product_uom(osv.Model):
    """
    like_type field let the sistem know wich is the unit type.
    It defines units, kg, boxes, mantles and palets.
    """
    _inherit = "product.uom"

    _columns = {
        'like_type': fields.selection([('units', 'Units'),
                                       ('kg', 'Kg'),
                                       ('boxes', 'Boxes'),
                                       ('mantles', 'Mantles'),
                                       ('palets', 'Palets')], 'Equals to',
                                      readonly=True),
    }
    _defaults = {
        'like_type': '',
    }
