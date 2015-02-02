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
{
    'name': 'Midban Telesale',
    'version': '1.0',
    'sequence': '19',
    'category': 'Sale',
    'description': """
    Midban Telesale
    Implements a telesale system optimized for fast orders.
    """,
    'data': [
        "wizard/ts_session_opening.xml",
        "telesale.xml",
        "telesale_sequence.xml",
        "sale_view.xml",
        'views/telesale.xml',
        'views/templates.xml',
    ],
    'depends': ['web', 'sale_stock', 'sale', 'sale_stock',
                'product_customer_restrict', 'midban_product',
                'crm', 'nan_partner_risk',
                'sale_product_substitute',
                'midban_depot_stock',
                'process_sale_order'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
