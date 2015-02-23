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
    "name": "Product Customer Restrict",
    "version": "1.0",
    "author": "Pexego",
    "category": "Custom",
    "website": "www.pexego.es",
    "description": """
    This module lets you restrict product to determinate customers.
    - You can define rules in partner model that indicates if you can see only
      products affected by rules or if you want to see all the products
      except those affected by rules.
    - You can define rules for a individual partner or group of partners.
    - Also allows you to put some products exclusives of determinate partner,
      so you can only sell this products to his exclusive partner.
    """,
    "images": [],
    "depends": ["base", "stock", "product"],
    "data": ['security/ir.model.access.csv',
             'partner_view.xml',
             'product_view.xml',
             ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
