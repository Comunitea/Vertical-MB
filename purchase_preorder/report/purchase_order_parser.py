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
from openerp import models, api, exceptions, _
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class purchase_order_parser(models.AbstractModel):
    """
    """

    _name = 'report.purchase_preorder.replenishement_purchase_order'

    def _get_products_suppliers(self, supplier_ids=[], cat_ids=[],):
        """
        Function that searches for products you can sell the supplier.
        """
        prod_tmp_ids = []
        prod_supp_info = self.env['product.supplierinfo']
        if supplier_ids:
            domain = [('name', 'in', supplier_ids)]
            prod_sup_objs = prod_supp_info.search(domain)
            if cat_ids:
                prod_tmp_ids = [x.product_tmpl_id.id for x in prod_sup_objs
                                if x.x.product_tmpl_id.categ_id in cat_ids]
            else:
                prod_tmp_ids = [x.product_tmpl_id.id for x in prod_sup_objs]

        return prod_tmp_ids

    def get_report_data(self, data):
        res = []
        # prod_objs = []
        # # Get products to give in the report
        # if data.get('product_ids', False):
        #     domain = [('product_tmpl_id', 'in', data['product_ids'])]
        #     prod_objs = self.env['product.product'].search(domain)
        #
        # elif data.get('supplier_ids', False):
        #     prod_tmp_ids = self._get_products_suppliers(data['supplier_ids'],
        #                                                 data['category_ids'])
        #     domain = [('product_tmpl_id', 'in', prod_tmp_ids)]
        #     prod_objs = self.env['product.product'].search(domain)
        #
        # elif data.get('category_ids', False):
        #     domain = [('categ_id', 'in', data['category_ids'])]
        #     prod_objs = self.env['product.product'].search(domain)
        #
        # if not prod_objs:
        #     raise except_orm(_("Error"),
        #                      _("No products founded for the search domain"))
        #
        # prod_ids = [x.id for x in prod_objs]
        #
        # t_sm = self.env['stock_move']
        # past_sales_domain = [
        #     ('date', '>=', data['start_date']),
        #     ('date', '<=', data['end_date']),
        #     ('state', '=', 'done'),
        #     ('product_id', 'in', prod_ids),
        #     ('picking_id.picking_type_code', '=', 'outgoing'),
        #     ('procurement_id.sale_line_id', '!=', False)
        # ]
        # past_sales_objs = t_sm.search(past_sales_domain)
        # for move in past_sales_objs:

        return res

    @api.multi
    def render_html(self, data=None):
        # import ipdb; ipdb.set_trace()

        report_obj = self.env['report']
        report_name = 'purchase_preorder.replenishement_purchase_order'
        # report = report_obj._get_report_from_name(report_name)
        stocks_dics = self.get_report_data(data)
        docargs = {
            'doc_ids': [],
            'doc_model': 'purchase_order',
            'docs': ["solo uno"],
            'stocks': stocks_dics
        }
        return report_obj.render(report_name, docargs)
