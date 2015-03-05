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
{
    "name": "Products Low Rotation",
    "version": "1.0",
    "author": "Pexego",
    "category": "Product",
    "website": "www.pexego.es",
    "description": """
PRODUCTS LOW ROTATION
=====================================================

Module that adds management rotations products.

Features:
--------------------------------------------------------
* They may define minimum rotation by product and by product category.
In case of having overlap will apply the minimum of product over the
product category.

* It will see a list of products below the minimum rotation.

* The rotation is calculated as follows:
AVG(movements out (this week -1), movements out (this week -2),
    movements out (this week -3), movements out (this week -4))

* It also adds a cron and a new menu to update the list of products
below the minimum.

    """,
    "images": [],
    "depends": ["base",
                "product",
                "stock"],
    "data": ["product_view.xml",
             "product_category_view.xml",
             "product_low_rotation_view.xml",
             "wizard/update_rotation_view.xml",
             "data/product_low_rotation_data.xml",
             "security/ir.model.access.csv"],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
