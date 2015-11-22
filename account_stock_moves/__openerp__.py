##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Comunitea.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
    'name': 'Accounting stock movements',
    'version': '1.2',
    'author': 'OpenERP SA, Veritos',
    'webbsite': 'https://www.odoo.com',
    'description': """""",
    'images': ['images/account_anglo_saxon.jpeg'],
    'depends': ['product', 'purchase', 'stock_picking_invoice_link'],
    'category': 'Accounting & Finance',
    'demo': [],
    'data': ['product_view.xml'],
    'test': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
