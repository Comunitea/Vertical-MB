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
    "name": "Price System Variable",
    "version": "1.0",
    "author": "Pexego",
    "category": "Custom",
    "website": "www.pexego.es",
    "description": """
    This module allows to manage variable prices and product pricelist.
    ==================================
    Defines the following pricelist based type rules:
    'Variable Price'
    'Change supplier costs'
    'Change product pvp'
    Depending of this field it will search for pricelist in differents models.
    """,
    "images": [],
    "depends": ["base", "product", "purchase", "sale"],
    "data": ['security/ir.model.access.csv',
             'sale_view.xml',
             'wizard/update_cmc_view.xml',
             'wizard/pvp_change_cmc_view.xml',
             'product_view.xml',
             'pricelist_view.xml',
             'price_data.xml',
             'purchase_view.xml',
             'table_pricelist_prices_view.xml'],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
