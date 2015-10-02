# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Carlos Lombardía Rodríguez$ <carlos@comunitea.com>
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
from openerp import models, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _
import time


class purchase_order_parser(models.AbstractModel):
    """
    """

    _name = 'report.purchase_preorder.replenishement_purchase_order'

    def _get_products_suppliers(self, fields, supplier_ids=[], cat_ids=[],):
        """
        Function that searches for products you can sell the supplier.
        """
        prod_dics = []
        prod_supp_info = self.env['product.supplierinfo']
        if supplier_ids:
            domain = [('name', 'in', supplier_ids)]
            prod_sup_objs = prod_supp_info.search(domain)
            prod_tmp_ids = [x.product_tmpl_id.id for x in prod_sup_objs]

            domain = [
                ('id', 'in', prod_tmp_ids),
                ('type', '=', 'product'),
            ]
            if cat_ids:
                domain.append(('categ_id', 'child_of', cat_ids))
            prod_dics = self.env['product.template'].search_read(domain,
                                                                 fields)
        return prod_dics

    def _get_stock_touple(self, prod, mode):
        unit = 0
        base = 0
        ba_un = prod['kg_un']
        if mode == 'stock':
            base = prod['qty_available']
        elif mode == 'incoming':
            base = prod['incoming_qty']
        elif mode == 'outgoing':
            base = prod['outgoing_qty']
        while base >= ba_un:
            base -= ba_un
            unit += 1
        return unit, int(round(base))

    def _get_diff_touple(self, dic_data):
        unit = 0
        base = 0
        sal_u = dic_data['sales'][0]
        sal_b = dic_data['sales'][1]
        pen_u = dic_data['pending'][0]
        pen_b = dic_data['pending'][1]
        stk_u = dic_data['stock'][0]
        stk_b = dic_data['stock'][1]
        inc_u = dic_data['incoming'][0]
        inc_b = dic_data['incoming'][1]
        out_u = dic_data['outgoing'][0]
        out_b = dic_data['outgoing'][1]
        unit = (sal_u + pen_u + out_u) - (stk_u + inc_u)
        base = (sal_b + pen_b + out_b) - (stk_b + inc_b)
        return unit, base

    def _get_to_order_touple(self, prod, diff_touple):
        palets = 0
        mantles = 0
        units = diff_touple[0]
        base = diff_touple[1]
        mantle_units = prod['kg_un'] * prod['un_ca'] * prod['ca_ma']
        palet_units = mantle_units * prod['ma_pa']

        total_units = 0
        if units > 0:
            total_units += units
        if base > 0:
            total_units += prod['kg_un'] and base / prod['kg_un'] or 0

        control = True
        while control:
            if total_units >= palet_units:
                palets += 1
            elif total_units >= mantle_units:
                mantles += 1
            else:
                control = False
        return palets, mantles

    def get_report_data(self, data):
        res = []
        prod_dics = []
        # Get products to give in the report
        fields = ['name', 'default_code', 'qty_available', 'incoming_qty',
                  'outgoing_qty', 'kg_un', 'un_ca', 'ca_ma', 'ma_pa']
        if data.get('product_ids', False):
            domain = [('id', 'in', data['product_ids']),
                      ('type', '=', 'product')]
            prod_dics = self.env['product.template'].search_read(domain,
                                                                 fields)

        elif data.get('supplier_ids', False):
            prod_dics = self._get_products_suppliers(fields,
                                                     data['supplier_ids'],
                                                     data['category_ids'])

        elif data.get('category_ids', False):
            domain = [('categ_id', 'child_of', data['category_ids']),
                      ('type', '=', 'product')]
            prod_dics = self.env['product.product'].search_read(domain, fields)

        if not prod_dics:
            raise except_orm(_("Error"),
                             _("No products founded for the search domain"))

        # prod_ids = [x.id for x in prod_dics]

        t_sm = self.env['stock.move']
        for prod in prod_dics:
            dic_data = {'code': prod['default_code'],
                        'name': prod['name'],
                        'sales': (0, 0),
                        'pending': (0, 0),  # No se usa, albaranes a revisar
                        'stock': self._get_stock_touple(prod, 'stock'),
                        'incoming': self._get_stock_touple(prod, 'incoming'),
                        'outgoing': self._get_stock_touple(prod, 'outgoing'),
                        'diff': (0, 0),
                        'to_order': (0, 0),
                        }
            past_sales_domain = [
                ('picking_id.min_date', '>=', data['start_date']),
                ('picking_id.min_date', '<=', data['end_date']),
                ('state', '=', 'done'),
                ('product_id.product_tmpl_id', '=', prod['id']),
                ('picking_id.picking_type_code', '=', 'outgoing'),
                ('procurement_id.sale_line_id', '!=', False)
            ]
            past_sales_objs = t_sm.search(past_sales_domain)
            uom_qty = 0.0
            for move in past_sales_objs:
                uom_qty += move.product_uom_qty
            dic_data['sales'] = self._get_stock_touple(prod, uom_qty)
            dic_data['diff'] = self._get_diff_touple(dic_data)
            dic_data['to_order'] = self._get_to_order_touple(prod,
                                                             dic_data['diff'])
            res.append(dic_data)
        return res

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report_name = 'purchase_preorder.replenishement_purchase_order'
        # report = report_obj._get_report_from_name(report_name)
        stocks_dics = self.get_report_data(data)

        filter_products = True if data['product_ids'] else False
        supplier_names = False
        category_names = False
        if not filter_products:
            supplier_names = ', '.join([x.name for x in
                                        self.env['res.partner'].
                                        browse(data['supplier_ids'])])

            category_names = ', '.join([x.name for x in
                                       self.env['product.category'].
                                       browse(data['category_ids'])])
        meta_info = {
            'print_date': time.strftime("%d/%m/%y %H:%M:%S"),
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'supplier_names': supplier_names,
            'category_names': category_names,
            'filter_products': filter_products,
        }
        docargs = {
            'doc_ids': [],
            'doc_model': 'purchase_order',
            'docs': ["solo uno"],
            'stocks': stocks_dics,
            'meta_info': meta_info
        }
        return report_obj.render(report_name, docargs)
