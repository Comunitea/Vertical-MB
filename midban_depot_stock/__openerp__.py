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
        "crm",
        "sale_stock",
        "stock_account",
        #"procurement_jit",
        "stock_picking_wave",
        "procurement",
        "purchase",
        "product",
        "product_expiry",
        "midban_partner",
        "midban_product",
        "midban_issue",
        # "price_system_variable",
        "l10n_es_toponyms",
        "report",
        "stock_valued_picking",
        "process_sale_order",  # Because of management of variable weigth
        "process_purchase_order",  # Because of management of variable weigth
        "web_dialog_size"  # In order to maximize wizard windows
    ],
    "data": [
        'res_users_view.xml',
        'stock_task_view.xml',
        'product_view.xml',
        'stock_machine_view.xml',
        'wizard/assign_task_wzd_view.xml',
        'wizard/reposition_wizard_view.xml',
        'wizard/stock_create_multipack_view.xml',
        "security/midban_depot_stock_security.xml",
        'security/ir.model.access.csv',
        'stock_vehicle_view.xml',
        'route_view.xml',
        'tag_view.xml',
        'partner_view.xml',
        'purchase_view.xml',
        'sale_view.xml',
        'account_view.xml',
        'stock_report.xml',
        'payment_view.xml',
        "wizard/stock_transfer_details.xml",
        "wizard/create_tag_wizard_view.xml",
        "wizard/create_camera_locations_view.xml",
        "wizard/get_route_detail_wzd_view.xml",
        "wizard/manual_transfer_wzd_view.xml",
        "wizard/validate_routes.xml",
        "wizard/stock_return_picking.xml",
        "wizard/set_detail_routes_view.xml",
        "wizard/several_procurement_product_view.xml",
        "wizard/operations_on_fly_wzd_view.xml",
        "wizard/confirm_load_wzd.xml",
        "wizard/revert_routes.xml",
        "wizard/batch_task.xml",
        'stock_view.xml',
        'procurement_view.xml',
        'crm_phonecall_view.xml',
        "data/product_data.xml",
        "data/stock_data.xml",
        "qweb_report/report_picking_task.xml",
        "qweb_report/report_picking_list.xml",
        "qweb_report/report_operations_list.xml",
        "qweb_report/report_delivery_list.xml",
        "qweb_report/report_stock_tag.xml",
        "qweb_report/report_supplier_order.xml",
        "qweb_report/report_supplier_reception.xml",
        "report/wave_report_view.xml",
        "report/route_report_view.xml",
        "report/out_picking_report_view.xml",
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
