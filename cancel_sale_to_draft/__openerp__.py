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
    "name": "Cancel Sale To Draft",
    "version": "1.0",
    "author": "Comunitea",
    "category": "custom",
    "website": "www.comunitea.es",
    "description": """
    * When cancel a sale order the related pickings will be canceled and the
      order will be set to Draft
    * Adds a Button in sale order to do it in one step.
    * Used in manual progress, and wait_risk states
    * Depends of OCA repository, and nan_partner_risk
    """,
    "images": [],
    "depends": ["sale", "sale_order_back2draft", "nan_partner_risk", "midban_depot_stock"],
    "data": [
        'views/sale_view.xml',
    ],
    "demo": [],
    "test": [],
    "installable": True,
}
