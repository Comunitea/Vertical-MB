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
    "name": "Midban Depot Stock",
    "version": "0.1",
    "author": "Pexego",
    "category": "Custom",
    "website": "www.pexego.es",
    "description": """
    Add Custom management of Midban Depot Stock Warehouse
    """,
    "images": [],
    "depends": [
        "base",
        "stock",
        "sale_stock",
        "procurement_jit",
        "stock_picking_wave",
        "sale",
        "procurement"
    ],
    "data": [
        'res_users_view.xml',
        'stock_task_view.xml',
        'stock_view.xml',
        'product_view.xml',
        'stock_machine_view.xml',
        'wizard/assign_task_wzd_view.xml',
        'wizard/reposition_wizard_view.xml',
        "security/midban_depot_stock_security.xml",
        'security/ir.model.access.csv',
        'stock_vehicle_view.xml',
        'route_view.xml',
        'partner_view.xml',
        'purchase_view.xml',
        'sale_view.xml',
        "wizard/route_assign_wizard_view.xml",
        "wizard/route_orders_wizard_view.xml"
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
