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
    "name": "Promotion",
    "version": "1.0",
    "author": "Pexego",
    "category": "Tools",
    "website": "www.pexego.es",
    "description": """
Promotions
=====================================================
  """,
    "images": [],
    "depends": ["base",
                "sale",
                "purchase",
                "stock",
                "stock_account",
                "purchase_preorder",
                "depot_edi",
                "midban_ultra_fresh"

                ],
    "data": [
             "security/ir.model.access.csv",
             "promotion_view.xml",
             "partner_view.xml",
             "purchase_view.xml",
             "purchase_preorder_view.xml",
             "data/account_data.xml",
             ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
