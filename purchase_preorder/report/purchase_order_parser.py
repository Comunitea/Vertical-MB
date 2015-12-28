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
    def _get_query_to_execute(self, data, select_query, prod_ids=False):
        SQL = ""
        if select_query == 'supp':
            if not prod_ids:
                if data.get('query_history', False):
                    # print("Supp con historial")
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
                    # print("Supp sin historial")
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
            else:
                if data.get('query_history', False):
                    # print("Supp sin historial y por productos de categoría")
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
                            AND pt.id in %s
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
                           AND pt.id in %s
                          GROUP by pt.id,p.default_code,pt.name,pt.uom_id,pt.active, part.name) as sub
                    GROUP by sub.id,sub.code,sub.name,sub.uom,sub.pname order by sub.name
                    """
                else:
                    # print("Supp sin historial y por productos de categoría")
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
                            AND pt.id in %s
                            AND pro.sale_line_id IS NOT NULL
                            GROUP by pt.id,p.default_code,pt.name,pt.uom_id,pt.active, part.name
                    """
        elif select_query == 'prod':
            if data.get('query_history', False):
                # print("Prod con historial")
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
                        AND pt.id in %s
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
                       AND pt.id in %s
                      GROUP by pt.id,p.default_code,pt.name,pt.uom_id,pt.active, part.name) as sub
                GROUP by sub.id,sub.code,sub.name,sub.uom,sub.pname order by sub.name
                """
            else:
                # print("Prod sin historial")
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
                        AND pt.id in %s
                        AND pro.sale_line_id IS NOT NULL
                        GROUP by pt.id,p.default_code,pt.name,pt.uom_id,pt.active, part.name
                """
        return SQL

    @api.multi
    def _by_supplier_query(self, data, wh_id, supplier_ids):
        fetch = []
        t_prod = self.env['product.template'].with_context(warehouse=wh_id)

        # SI A MAYORES HAY QUE FILTRAR POR CATEGORÍA
        cat_ids = data.get('category_ids', []) and data['category_ids'] or []
        prod_ids = []  # Productos hijos de las categorías indicadas
        if cat_ids:
           domain = [('categ_id', 'child_of', cat_ids),
                     ('type', '=', 'product')]
           prod_objs = t_prod.search(domain)
           prod_ids_lst = [x.id for x in prod_objs]
           prod_ids = tuple(prod_ids_lst)
        SQL = self._get_query_to_execute(data, 'supp', prod_ids=prod_ids)
        start_date = data['start_date'] + " 00:00:00"
        end_date =  data['end_date'] + " 23:59:59"
        supplier_touple = tuple(supplier_ids)
        if data.get('query_history', False):
            if not prod_ids:
                self._cr.execute(SQL,(start_date, end_date, supplier_touple, start_date, end_date, supplier_touple))
            else: # Filtramos por productos específicos de la categoría
                self._cr.execute(SQL,(start_date, end_date, supplier_touple, prod_ids, start_date, end_date, supplier_touple, prod_ids))
        else:
            if not prod_ids:
                self._cr.execute(SQL,(start_date, end_date, supplier_touple))
            else: # Filtramos por productos específicos de la categoría
                self._cr.execute(SQL,(start_date, end_date, supplier_touple, prod_ids))
        fetch = self._cr.fetchall()
        return fetch

    @api.multi
    def _by_products_query(self, data, wh_id, prod_ids):
        fetch = []
        t_prod = self.env['product.template'].with_context(warehouse=wh_id)
        SQL = self._get_query_to_execute(data, 'prod')
        start_date = data['start_date'] + " 00:00:00"
        end_date =  data['end_date'] + " 23:59:59"
        product_touple = tuple(prod_ids)
        if data.get('query_history', False):
            self._cr.execute(SQL,(start_date, end_date, product_touple, start_date, end_date, product_touple))
        else:
            self._cr.execute(SQL,(start_date, end_date, product_touple))
        fetch = self._cr.fetchall()
        return fetch

    def _discard_rec(self, rec, prod_data, data):
        discard = False
        if data.get('product_temp_ids', False):
            if prod_data[rec[0]]['temp_type'] and \
                    prod_data[rec[0]]['temp_type'][0] \
                    not in data['product_temp_ids']:
                discard = True
        return discard

    def _discard_dic_data(self, dic_data, data):
        discard = False
        mode = False
        if data.get('show_to_buy', False):
            mode = data['show_to_buy']
        if mode == 'man_pal' and not (dic_data['to_order'][0] > 0 or dic_data['to_order'][1] > 0):
            discard = True
        elif mode == 'diff_pos' and not (dic_data['diff'] > 0):
            discard = True
        return discard

    def _process_query_result(self, data, wh_id, prod_ids, fetch):
        by_supplier = {}
        t_prod = self.env['product.template'].with_context(warehouse=wh_id)
        fields = ['uom_id','qty_available', 'outgoing_qty', 'incoming_qty',
                  'kg_un', 'un_ca', 'ca_ma', 'ma_pa', 'temp_type']
        prod_read = t_prod.browse(prod_ids).read(fields)
        prod_data = {}
        for rec in prod_read:
            prod_data[rec['id']] = rec
        for rec in fetch:
            if self._discard_rec(rec, prod_data, data):
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
            # Si no tiene marca para o tiene y los valores cumplen la condición, añado.
            if not self._discard_dic_data(dic_data, data):
                if rec[5] not in by_supplier:
                    by_supplier[rec[5]] = []
                by_supplier[rec[5]].append(dic_data)
        return by_supplier

    @api.multi
    def _add_not_sold_prods(self, fetch, supplier_ids, prod_ids):
        res = fetch

        SQL = """
            select pt.id, pp.default_code, pt.name, pt.uom_id,  0,  part.name
            FROM product_supplierinfo ps
            INNER JOIN product_template pt ON pt.id = ps.product_tmpl_id
            INNER JOIN product_product pp ON pp.product_tmpl_id = pt.id
            INNER JOIN res_partner part ON ps.name = part.id
            WHERE part.id = %s
            AND pt.id not in %s

        """
        self._cr.execute(SQL,(tuple(supplier_ids), tuple(prod_ids)))
        fetch2 = self._cr.fetchall()
        res.extend(fetch2)
        return res

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

        # FILTRO PORDUCTOS ESPECÍFICOS
        if data.get('filter_options', False) and data['filter_options']== 'products':
            if not data.get('product_ids', False):
                raise except_orm(_("Error"), _("Seleccione al menos un producto."))
            domain = [('id', 'in', data['product_ids']),
                      ('type', '=', 'product')]
            if data['product_temp_ids']:
                domain.append(('temp_type', 'in', data['product_temp_ids']))
            prod_objs = t_prod.search(domain)

        # FILTRO POR PROVEEDORES CON O SIN CATEGORÍAS
        elif data.get('supplier_ids', []) or \
                     (data.get('filter_range', False) and data['from_range'][0] and data['from_range'][1]):
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

        # SE DISTINGE EN SI SE ESPECIFICARON PROVEEDORES O PRODUCTOS
        fetch = []
        if supplier_ids:  # Se pidieron proveedores y/o categorías
            fetch = self._by_supplier_query(data, wh_id, supplier_ids)
        elif prod_objs:  # Se pidieron o bien productos solos, o bien categ
            prod_ids = [x.id for x in prod_objs]
            fetch = self._by_products_query(data, wh_id, prod_ids)

        # PROCESAMOS QUERY AGRUPANDO POR PROVEEDOR
        add_prod = data.get('no_sale', False)
        if fetch:
            prod_ids = [x[0] for x in fetch]
            if add_prod and supplier_ids:
                fetch = self._add_not_sold_prods(fetch, supplier_ids, prod_ids)
                prod_ids = [x[0] for x in fetch]
            by_supplier = self._process_query_result(data, wh_id, prod_ids, fetch)
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
