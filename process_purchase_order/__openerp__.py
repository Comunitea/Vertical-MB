# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 20015 Comunitea Servicios Tecnológicos  All Rights Reserved
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
{
    "name": "Process Purchase Order",
    "version": "1.0",
    "author": "Comunitea",
    "category": "custom",
    "website": "www.comunitea.com",
    "description": """
    * Management of purchase order based on logistic units defined in products
      supplier record
    * Posibility of buy in different units of measure
    * Management of conversions between prices and units of purchase

    """,
    "images": [],
    "depends": ["base",
                "midban_product",  # log_base_id, base_use_field... fields
                "purchase",
                ],
    "data": [
        'purchase_view.xml',
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
