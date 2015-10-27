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
    "name": "Process Sale Order",
    "version": "1.0",
    "author": "Pexego",
    "category": "custom",
    "website": "www.pexego.es",
    "description": """
    * Only sales in units or boxes.
    * Minimum sale unit in product tab.
    * Possibility of only sale in units, avoiding to sale in boxes.
    * Box sales are linked to units prices.
    * Box sales are linked to units prices.
    * Automatic computation of the best combination of boxes / units

    """,
    "images": [],
    "depends": ["base",
                "midban_product",  # log_base_id, base_use_field... fields
                "sale",
                "sale_stock",
                # "midban_depot_stock", #because overwrite action_ship_create
                ],
    "data": [
        'product_view.xml',
        'sale_view.xml',
        'security/ir.model.access.csv',
        'stock_view.xml',
        'cron_table_data.xml',
        'table_pricelist_prices_view.xml',
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
