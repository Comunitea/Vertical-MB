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
##############################################################################
{
    "name": "Midban Ultra Fresh",
    "version": "1.0",
    "author": "Pexego",
    "category": "custom",
    "website": "www.pexego.es",
    "description": """
    * Manage ultrafresh products
    """,
    "images": [],
    "depends": [
        "base",
        "sale",
        "purchase",
        "stock",
        "midban_product",  # Beacause of field product_class (for ultrafresh)
        "midban_depot_stock",
        # "process_sale_order",  # Beacause of _amount_line and choose_unit
    ],
    "data": [
        'data/ultra_fresh_data.xml',
        'wizard/calc_ultrafresh_price_wzd_view.xml',
        'purchase_view.xml',
        'ultrafresh_report.xml',
        'qweb_report/ultrafresh_purchase_report.xml',
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
