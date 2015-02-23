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
    "name": "Depot Cross Dock",
    "version": "1.0",
    "author": "Pexego",
    "category": "custom",
    "website": "www.pexego.es",
    "description": """
    * When you sale a low rotation products, get products by buying to
      midban central warehouse.
    * When you sale a cross-dock products, get products from suppliers by
      buying to suppliers.
    * Purchase orders to midban and cross-docking suppiers must have a
      drop code.

    """,
    "images": [],
    "depends": ["base",
                "product",
                "purchase",
                "sale",
                "procurement",
                "midban_depot_stock",
                ],
    "data": [
        'partner_view.xml',
        'procurement_view.xml',
        'wizard/process_cross_dock_wzd_view.xml',
        'data/depot_cross_dock_data.xml',
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
