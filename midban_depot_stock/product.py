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

class product_template(osv.Model):
    """
    Adding field picking location
    """
    _inherit = "product.template"

    _columns = {
        'picking_location_id': fields.many2one('stock.location',
                                               'Location Picking',
                                               required=True,
                                               domain=[('usage', '=',
                                                        'internal')]),
    }
    _sql_constraints = [
        ('location_id_uniq', 'unique(picking_location_id)',
         _("Field Location picking is already setted"))
    ]
