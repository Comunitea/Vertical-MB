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


class product_product(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'products_substitute_ids': fields.many2many('product.template',
                                                    'product_subtitutes_rel',
                                                    'product_id',
                                                    'substitute_id',
                                                    'Substitute product'),
        # It doubles the many2many field by reversing the order of the keys
        # to making a domain in the wizard to substitute product. In the 7.0
        # version can't deploy python code in xml files.
        'products_parent_ids': fields.many2many('product.template',
                                                'product_subtitutes_rel',
                                                'substitute_id',
                                                'product_id',
                                                'Parent product'),
    }
