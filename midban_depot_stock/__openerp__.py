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
        "mail",
        "email_template",
        "sale_stock",
    ],
    "data": [
        'security/ir.model.access.csv',
        'stock_view.xml'
    ],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
