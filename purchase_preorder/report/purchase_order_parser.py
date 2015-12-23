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
import time


# class purchase_order_parser(models.AbstractModel):
#     """
#     """
#     _name = 'report.purchase_preorder.replenishement_purchase_order'
#
#     def _get_products_suppliers(self, fields, wh_id, from_range=[], supplier_ids=[], cat_ids=[], product_temp_ids=[]):
#         """
#         Function that searches for products you can sell the supplier.
#         """
#         get_supplier_t = time.time()
#         prod_dics = []
#         prod_supp_info = self.env['product.supplierinfo']
#         if from_range and from_range[0] and from_range[1]:
#             supplier_ids = []
#             supplier_objs = self.env['res.partner'].search([('supplier', '=', True)])
#             for sup in supplier_objs:
#                 if sup.ref and sup.ref.isdigit() \
#                         and int(sup.ref) >= from_range[0] \
#                         and int(sup.ref) <= from_range[1]:
#                     supplier_ids.append(sup.id)
#         if supplier_ids:
#             domain = [('name', 'in', supplier_ids)]
#             prod_sup_objs = prod_supp_info.search(domain)
#             prod_tmp_ids = [x.product_tmpl_id.id for x in prod_sup_objs]
#
#             domain = [
#                 ('id', 'in', prod_tmp_ids),
#                 ('type', '=', 'product'),
#             ]
#             if product_temp_ids:
#                 domain.append(('temp_type', 'in', product_temp_ids))
#             if cat_ids:
#                 domain.append(('categ_id', 'child_of', cat_ids))
#             prod_dics = self.env['product.template'].with_context(warehouse=wh_id).search_read(domain,
#                                                                  fields)
#         print("************************************************************")
#         print("Obtener proveedores")
#         print(time.time() -get_supplier_t)
#         print("************************************************************")
#         return prod_dics
#
#     def _get_stock(self, prod, mode):
#         base = 0
#         comp = 0
#         qty = 0
#         comp_base = prod['kg_un']
#         base_container = prod['un_ca']
#         if mode == 'stock':
#             qty = prod['qty_available']
#         elif mode == 'incoming':
#             qty = prod['incoming_qty']
#         elif mode == 'outgoing':
#             qty = prod['outgoing_qty']
#         else:
#             qty = mode
#         return qty
#
#     def _get_diff(self, dic_data):
#         sal_u = dic_data['sales']
#         pen_u = dic_data['pending']
#         stk_u = dic_data['stock']
#         inc_u = dic_data['incoming']
#         out_u = dic_data['outgoing']
#         diff = (sal_u + pen_u + out_u) - (stk_u + inc_u)
#         return diff
#
#     def _get_to_order_touple(self, prod, diff_touple):
#         palets = 0
#         mantles = 0
#         diff = diff_touple
#         mantle_units = prod['kg_un'] * prod['un_ca'] * prod['ca_ma']
#         palet_units = mantle_units * prod['ma_pa']
#
#
#         control = True
#         while control:
#             if diff >= palet_units:
#                 palets += 1
#                 diff -= palet_units
#             elif diff >= mantle_units:
#                 mantles += 1
#                 diff -= mantle_units
#             else:
#                 control = False
#         return palets, mantles
#
#     def get_report_data(self, data):
#         res = []
#         prod_dics = []
#         t_prod = self.env['product.template']
#         wh_objs = self.env['stock.warehouse'].search([])
#         wh_id = False
#         if wh_objs:
#             wh_id = wh_objs[0].id
#         # Get products to give in the report
#         fields = ['name', 'default_code', 'qty_available', 'incoming_qty',
#                   'outgoing_qty', 'kg_un', 'un_ca', 'ca_ma', 'ma_pa',
#                   'log_base_id', 'log_unit_id', 'log_box_id', 'uom_id']
#         if data.get('product_ids', False):
#             domain = [('id', 'in', data['product_ids']),
#                       ('type', '=', 'product')]
#             if data['product_temp_ids']:
#                 domain.append(('temp_type', 'in', data['product_temp_ids']))
#             prod_dics = t_prod.with_context(warehouse=wh_id).search_read(domain,
#                                                                  fields)
#
#         elif data.get('supplier_ids', False) or data.get('from_range', False):
#             prod_dics = self._get_products_suppliers(fields,
#                                                      wh_id,
#                                                      data['from_range'],
#                                                      data['supplier_ids'],
#                                                      data['category_ids'],
#                                                      data['product_temp_ids'])
#
#         elif data.get('category_ids', False):
#             domain = [('categ_id', 'child_of', data['category_ids']),
#                       ('type', '=', 'product')]
#             prod_dics = t_prod.with_context(warehouse=wh_id).search_read(domain,
#                                                                  fields)
#
#         if not prod_dics:
#             raise except_orm(_("Error"),
#                              _("No products founded for the search domain"))
#
#         # prod_ids = [x.id for x in prod_dics]
#
#         t_sm = self.env['stock.move']
#         t_sol = self.env['sale.order.line']
#         t_un = self.env['product.uom']
#         print len(prod_dics)
#         for prod in prod_dics:
#             print("************************************************************")
#             print("producto %s" %  prod['name'])
#             print("************************************************************")
#             t_ita = time.time()
#             stock_unit = t_un.browse(prod['uom_id'][1])
#             dic_data = {'code': prod['default_code'],
#                         'name': prod['name'],
#                         'stock_unit': stock_unit,
#                         'sales': 0.0000,
#                         'pending': 0.0000,  # No se usa, albaranes a revisar
#                         'stock': self._get_stock(prod, 'stock'),
#                         'incoming': self._get_stock(prod, 'incoming'),
#                         'outgoing': self._get_stock(prod, 'outgoing'),
#                         'diff': 0.0000,
#                         'to_order': (0.0000, 0.0000),
#                         }
#             # past_sales_domain = [
#             #     ('picking_id.min_date', '>=', data['start_date']),
#             #     ('picking_id.min_date', '<=', data['end_date']),
#             #     ('state', '=', 'done'),
#             #     ('product_id.product_tmpl_id', '=', prod['id']),
#             #     ('picking_id.picking_type_code', '=', 'outgoing'),
#             #     ('procurement_id.sale_line_id', '!=', False)
#             # ]
#             # past_sales_objs = t_sm.search(past_sales_domain)
#             # uom_qty = 0.0
#             # for move in past_sales_objs:
#             #     uom_qty += move.product_uom_qty
#
#             SQL = """
#                 SELECT sum(product_uom_qty)
#                 FROM stock_move sm
#                 INNER JOIN stock_picking sp ON sp.id = sm.picking_id
#                 INNER JOIN procurement_order pro ON pro.id = sm.procurement_id
#                 INNER JOIN product_product p ON p.id = sm.product_id
#                 INNER JOIN product_template pt ON pt.id = p.product_tmpl_id
#                 WHERE sp.state = 'done'
#                 AND sp.min_date >= %s
#                 AND sp.min_date <= %s
#                 AND pt.id = %s
#                 AND pro.sale_line_id IS NOT NULL
#             """
#
#             self._cr.execute(SQL,(data['start_date'], data['end_date'],
#                                   prod['id']))
#             fetch = self._cr.fetchall()
#             uom_qty = 0
#             if fetch and fetch[0] and fetch[0][0] is not None:
#                 uom_qty += fetch[0][0]
#             SQL = """ SELECT sum(product_uom_qty)
#                       FROM sale_order_line sol
#                       INNER JOIN sale_order so ON so.id = sol.order_id
#                       INNER JOIN product_product p ON p.id = sol.product_id
#                       INNER JOIN product_template pt ON pt.id = p.product_tmpl_id
#                       WHERE so.state in ('history')
#                       AND so.date_order >= %s
#                       AND so.date_order <= %s
#                       AND pt.id = %s
#                       """
#             self._cr.execute(SQL, (data['start_date'], data['end_date'],
#                                    prod['id']))
#             fetch = self._cr.fetchall()
#             if fetch and fetch[0] and fetch[0][0] is not None:
#                 uom_qty += fetch[0][0]
#
#             dic_data['sales'] = self._get_stock(prod, uom_qty)
#             dic_data['diff'] = self._get_diff(dic_data)
#             dic_data['to_order'] = self._get_to_order_touple(prod,
#                                                              dic_data['diff'])
#
#             if data['show_to_buy']:
#                 if dic_data['to_order'][0] > 0 or dic_data['to_order'][1] > 0:
#                     res.append(dic_data)
#             else:
#                 res.append(dic_data)
#             print("************************************************************")
#             print("Iteración:")
#             print(time.time() - t_ita)
#             print("************************************************************")
#         return res
#
#     @api.multi
#     def render_html(self, data=None):
#         report_obj = self.env['report']
#         report_name = 'purchase_preorder.replenishement_purchase_order'
#         # report = report_obj._get_report_from_name(report_name)
#         if not data:
#             raise except_orm(_('Error'),
#                              _('You must print it from a wizard'))
#         stocks_dics = self.get_report_data(data)
#         if not stocks_dics:
#             raise except_orm(_("Error"),
#                              _("No products founded for the search domain"))
#         filter_products = True if data['product_ids'] else False
#         supplier_names = False
#         category_names = False
#         if not filter_products:
#             supplier_names = ', '.join([x.name for x in
#                                         self.env['res.partner'].
#                                         browse(data['supplier_ids'])])
#
#             category_names = ', '.join([x.name for x in
#                                        self.env['product.category'].
#                                        browse(data['category_ids'])])
#         meta_info = {
#             'print_date': time.strftime("%d/%m/%y %H:%M:%S"),
#             'start_date': data['start_date'],
#             'end_date': data['end_date'],
#             'supplier_names': supplier_names,
#             'category_names': category_names,
#             'filter_products': filter_products,
#             'filter_range': data['filter_range'],
#             'from_range': data['from_range']
#         }
#         docargs = {
#             'doc_ids': [],
#             'doc_model': 'purchase_order',
#             'docs': ["solo uno"],
#             'stocks': stocks_dics,
#             'meta_info': meta_info
#         }
#         return report_obj.render(report_name, docargs)


class purchase_order_parser(models.AbstractModel):
    """
    """
    _name = 'report.purchase_preorder.replenishement_purchase_order'

    def _get_diff(self, dic_data):
        sal_u = dic_data['sales']
        stk_u = dic_data['stock']
        inc_u = dic_data['incoming']
        out_u = dic_data['outgoing']
        diff = (sal_u + out_u) - (stk_u + inc_u)
        return diff

    def _get_to_order_touple(self, diff_touple, pdata):
        palets = 0
        mantles = 0
        diff = diff_touple
        mantle_units = pdata['kg_un'] * pdata['un_ca'] * pdata['ca_ma']
        palet_units = mantle_units * pdata['ma_pa']
        control = True
        while control:
            if diff >= palet_units:
                palets += 1
                diff -= palet_units
            elif diff >= mantle_units:
                mantles += 1
                diff -= mantle_units
            else:
                control = False
        return palets, mantles

    def _get_supplier_ids(self, data):
        supplier_ids = data.get('supplier_ids', [])
        from_range = data['from_range']
        if from_range and from_range[0] and from_range[1]:
            supplier_ids = []
            supplier_objs = self.env['res.partner'].search([('supplier', '=', True)])
            for sup in supplier_objs:
                if sup.ref and sup.ref.isdigit() \
                        and int(sup.ref) >= from_range[0] \
                        and int(sup.ref) <= from_range[1]:
                    supplier_ids.append(sup.id)
        return supplier_ids

    @api.multi
    def _get_query_to_execute(self, data, select_query):
        SQL = ""
        if select_query == 'supp':
            if data.get('query_history', False):
                SQL = """
                SELECT sub.id,sub.code,sub.name,sub.uom,sum(sub.sum_uom), sub.pname from(
                    SELECT pt.id as id,p.default_code as code,pt.name as name,pt.uom_id as uom,sum(sm.product_uom_qty) as sum_uom, part.name as pname
                        FROM stock_move sm
                        INNER JOIN stock_picking sp ON sp.id = sm.picking_id
                        INNER JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                        INNER JOIN procurement_order pro ON pro.id = sm.procurement_id
                        INNER JOIN product_product p ON p.id = sm.product_id
                        INNER JOIN product_template pt ON pt.id  = p.product_tmpl_id AND pt.active = True and pt.type = 'product'
                        INNER JOIN product_supplierinfo psupp ON psupp.product_tmpl_id = pt.id
                        INNER JOIN res_partner part ON psupp.name = part.id
                        WHERE sp.state = 'done'
                        AND spt.code = 'outgoing'
                        AND sp.min_date >= %s
                        AND sp.min_date <= %s
                        AND part.id in %s
                        AND pro.sale_line_id IS NOT NULL
                        GROUP by pt.id,p.default_code,pt.name,pt.uom_id,pt.active, part.name
                    UNION
                    SELECT pt.id as id, p.default_code as code,pt.name as name,pt.uom_id as uom,sum(sol.product_uom_qty) as sum_uom, part.name as pname
                       FROM sale_order_line sol
                       INNER JOIN sale_order so ON so.id = sol.order_id
                       INNER JOIN product_product p ON p.id = sol.product_id
                       INNER JOIN product_template pt ON pt.id = p.product_tmpl_id
                       INNER JOIN product_supplierinfo psupp ON psupp.product_tmpl_id = pt.id
                       INNER JOIN res_partner part ON psupp.name = part.id
                       WHERE so.state in ('history')
                       AND so.date_order  >= %s
                       AND so.date_order  <= %s
                       AND part.id in %s
                      GROUP by pt.id,p.default_code,pt.name,pt.uom_id,pt.active, part.name) as sub
                GROUP by sub.id,sub.code,sub.name,sub.uom,sub.pname order by sub.name
                """
            else:
                SQL = """
                    SELECT pt.id as id,p.default_code as code,pt.name as name,pt.uom_id as uom,sum(sm.product_uom_qty) as sum_uom, part.name as pname
                        FROM stock_move sm
                        INNER JOIN stock_picking sp ON sp.id = sm.picking_id
                        INNER JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                        INNER JOIN procurement_order pro ON pro.id = sm.procurement_id
                        INNER JOIN product_product p ON p.id = sm.product_id
                        INNER JOIN product_template pt ON pt.id  = p.product_tmpl_id AND pt.active = True and pt.type = 'product'
                        INNER JOIN product_supplierinfo psupp ON psupp.product_tmpl_id = pt.id
                        INNER JOIN res_partner part ON psupp.name = part.id
                        WHERE sp.state = 'done'
                        AND spt.code = 'outgoing'
                        AND sp.min_date >= %s
                        AND sp.min_date <= %s
                        AND part.id in %s
                        AND pro.sale_line_id IS NOT NULL
                        GROUP by pt.id,p.default_code,pt.name,pt.uom_id,pt.active, part.name
                """
        return SQL

    @api.multi
    def _by_supplier_query(self, data, wh_id, supplier_ids):
        by_supplier = {}
        t_prod = self.env['product.template'].with_context(warehouse=wh_id)
        SQL = self._get_query_to_execute(data, 'supp')
        start_date = data['start_date'] + " 00:00:00"
        end_date =  data['end_date'] + " 23:59:59"
        supplier_touple = tuple(supplier_ids)
        if data.get('query_history', False):
            self._cr.execute(SQL,(start_date, end_date, supplier_touple, start_date, end_date, supplier_touple))
        else:
            self._cr.execute(SQL,(start_date, end_date, supplier_touple))
        fetch = self._cr.fetchall()

        prod_ids = [x[0] for x in fetch]
        fields = ['uom_id','qty_available', 'outgoing_qty', 'incoming_qty',
                  'kg_un', 'un_ca', 'ca_ma', 'ma_pa', 'temp_type']
        prod_read = t_prod.browse(prod_ids).read(fields)
        prod_data = {}
        for rec in prod_read:
            prod_data[rec['id']] = rec
        for rec in fetch:
            if data.get('product_temp_ids', False):
                if prod_data[rec[0]]['temp_type'] and \
                        prod_data[rec[0]]['temp_type'][0] \
                        not in data['product_temp_ids']:
                    continue
            dic_data = {
                'code': rec[1],
                'name':rec[2],
                'stock_unit':prod_data[rec[0]]['uom_id'][1],
                'sales':rec[4],
                'stock': prod_data[rec[0]]['qty_available'],
                'incoming': prod_data[rec[0]]['incoming_qty'],
                'outgoing': prod_data[rec[0]]['outgoing_qty'],
            }
            dic_data['diff'] = self._get_diff(dic_data)
            dic_data['to_order'] = self._get_to_order_touple(dic_data['diff'], prod_data[rec[0]])
            if (not data.get('show_to_buy', False)) or \
                    (data.get('show_to_buy', False) and \
                    dic_data['to_order'][0] > 0 or \
                    dic_data['to_order'][1] > 0):
                if rec[5] not in by_supplier:
                    by_supplier[rec[5]] = []
                by_supplier[rec[5]].append(dic_data)
                by_supplier[rec[5]].append(dic_data)
        return by_supplier

    @api.multi
    def get_report_data(self, data):
        """
        :param data: Filters of the wizard
        :return: dic with suppliers as keys and a list of products data dics
        as values. We need it this way because we always want to print products
        suppliers in a diferent page for each_one
        """
        by_supplier = {}
        wh_objs = self.env['stock.warehouse'].search([])
        wh_id = False
        if wh_objs:
            wh_id = wh_objs[0].id
        # warehouse en contexto para que nos de los stocks de ese almacén
        t_prod = self.env['product.template'].with_context(warehouse=wh_id)
        self.env['product.template'].with_context(warehouse=wh_id)
        supplier_ids = False
        prod_objs = False
        # FILTRO PORDUCTOS ESPECCÍFICOS
        if data.get('filter_options', False) and data['filter_options']== 'products':
            if not data.get('product_ids', False):
                raise except_orm(_("Error"),
                                 _("Seleccione al menos un producto."))
            domain = [('id', 'in', data['product_ids']),
                      ('type', '=', 'product')]
            if data['product_temp_ids']:
                domain.append(('temp_type', 'in', data['product_temp_ids']))
            prod_objs = t_prod.search(domain)

        # FILTRO POR PROVEEDORES CON O SIN CATEGORÍAS
        elif data.get('supplier_ids', []) or data.get('filter_range', False):
            supplier_ids = self._get_supplier_ids(data)
            if not supplier_ids:
                raise except_orm(_("Error"),
                                 _("No hay proveedores que buscar"))
        # FILTRO SOLO POR CATEGORÍA
        elif data.get('category_ids', False):
            domain = [('categ_id', 'child_of', data['category_ids']),
                      ('type', '=', 'product')]
            if data['product_temp_ids']:
                domain.append(('temp_type', 'in', data['product_temp_ids']))
            prod_objs = t_prod.search(domain)

        if supplier_ids:  # Se pidieron proveedores y/o categorías
            by_supplier = self._by_supplier_query(data, wh_id, supplier_ids)
        elif prod_objs:
            raise except_orm(_("Error"),
                             _("No permitido filtrar por productos/categorias de momento"))


        return by_supplier


    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report_name = 'purchase_preorder.replenishement_purchase_order'
        # report = report_obj._get_report_from_name(report_name)
        if not data:
            raise except_orm(_('Error'),
                             _('You must print it from a wizard'))
        stocks_dics = self.get_report_data(data)
        if not stocks_dics:
            raise except_orm(_("Error"),
                             _("No products founded for the search domain"))
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
            'filter_range': data['filter_range'],
            'from_range': data['from_range']
        }
        docargs = {
            'doc_ids': [],
            'doc_model': 'purchase_order',
            'docs': stocks_dics.keys(),
            'stocks': stocks_dics,
            'meta_info': meta_info
        }
        return report_obj.render(report_name, docargs)
