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
    "name": "Midban Product",
    "version": "1.0",
    "author": "Pexego",
    "category": "HR",
    "website": "www.pexego.es",
    "description": """
    This module add custom fields an behavior for MIDBAN product.

    Creates a statusbar inProducts view with the following states:
        Validate pending
        Logistic validation pending
        Comercial validation pending
        Validated
        Registered
        Unregistered
        Denied

    When you create a Product is desactived by defaut until state
    change to register.
    You can see the products in registering process or unregistered products
    using filters.

    This module adds a history in products that record states changes
    and changes dates.

    Provides a model of denied register reasons selected when you unregister a
    partner. Provides a wizard to do that.

    Provides a model of unregister reasons selected when you unregister a
    partner. Provides a wizard to do that.

    It adds a unique secuence of each product on internal reference field

    Adds a model of product allergens that you can select in product view.

    The configuration of new models can be seen in configuration menu of
    sales and purchases.
    """,
    "images": [],
    "depends": ["base",
                "product",
                "purchase",
                "account",
                "product_unique_default_code",
                "sale",
                "stock_account",
                "stock"],
    "data": ["wizard/process_unregister_product_view.xml",
             "wizard/process_deny_product_view.xml",
             "product_view.xml",
             "product_sequence.xml",
             "product_workflow.xml",
             'security/ir.model.access.csv',
             'product_data.xml',
             'data/midban_product_price_type_data.xml',
             'wizard/set_order_category_products_view.xml'],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
