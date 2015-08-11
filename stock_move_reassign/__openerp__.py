# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicos Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
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
    'name': 'Stock move reassign',
    'version': '1.0',
    'category': 'Stock',
    'description': """Allow to change move assignation from move inside
 picking. Release other assigned quants for allowing assign current move""",
    'author': 'Comunitea Servicios Tecnológicos',
    'website': '',
    "depends": ['stock'],
    "data": ["wizard/reassign_stock_wzd_view.xml",
             "stock_view.xml"],
    "installable": True
}

