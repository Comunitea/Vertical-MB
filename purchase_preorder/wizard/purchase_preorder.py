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
from openerp.osv import osv, fields
import time
import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import models, api, fields as fields2


PRODUCT_STATE_SELECTION = [('val_pending', 'Validate pending'),
                           ('logic_pending', 'Logistic validation pending'),
                           ('commercial_pending',
                            'Comercial validation pending'),
                           ('validated', 'Validated'),
                           ('registered', 'Registered'),
                           ('unregistered', 'Unegistered'),
                           ('denied', 'Denied')]


class purchase_preorder(osv.Model):
    _name = 'purchase.preorder'
    _description = ''

    def _get_totals(self, cr, uid, ids, field_name, arg, context=None):
        """
        Returns the sum of the amount, boxes, palets and mantles all lines
        of pre-order.
        """
        res = {}
        for preorder in self.browse(cr, uid, ids, context=context):
            res[preorder.id] = {
                'total': 0.0,
                'palets': 0.0,
                'mantles': 0.0,
                'boxes': 0.0,
                'min_palets': 0.0,
                'remaining_palets': 0.0}
            subtotal = 0.0
            palets = 0.0
            mantles = 0.0
            boxes = 0.0
            if preorder.product_supplier_ids:
                for line in preorder.product_supplier_ids:
                    if line.subtotal:
                        subtotal += line.subtotal
                    if line.palets:
                        palets += line.palets
                    if line.mantles:
                        mantles += line.mantles
                    if line.boxes:
                        boxes += line.boxes
                res[preorder.id]['total'] = subtotal
                res[preorder.id]['palets'] = palets
                res[preorder.id]['mantles'] = mantles
                res[preorder.id]['boxes'] = boxes
                res[preorder.id]['min_palets'] = \
                    preorder.supplier_id.min_palets
                if palets < res[preorder.id]['min_palets']:
                    diff = res[preorder.id]['min_palets'] - \
                        res[preorder.id]['min_palets']
                else:
                    diff = 0
                res[preorder.id]['remaining_palets'] = diff
        return res

    _columns = {
        'name': fields.char('Name', size=255, required=True, readonly=True),
        'supplier_id': fields.many2one('res.partner',
                                       'Supplier',
                                       required=True),
        'product_supplier_ids': fields.one2many('products.supplier',
                                                'preorder_id',
                                                'Products Supplier',
                                                domain=[('product_uoc_qty','>',0)]),
        'total': fields.function(_get_totals,
                                 type="float",
                                 string='Amount total',
                                 readonly=True,
                                 multi="totals"),
        'palets': fields.function(_get_totals,
                                  type="float",
                                  string='Palets',
                                  readonly=True,
                                  multi="totals"),
        'mantles': fields.function(_get_totals,
                                   type="float",
                                   string='Mantles',
                                   readonly=True,
                                   multi="totals"),
        'boxes': fields.function(_get_totals,
                                 type="float",
                                 string='Boxes',
                                 readonly=True,
                                 multi="totals"),
        'min_palets': fields.function(_get_totals,
                                      type="float",
                                      string='Min. Palets',
                                      readonly=True,
                                      multi="totals"),
        'remaining_palets': fields.function(_get_totals,
                                            type="float",
                                            string='Remaining Palets',
                                            readonly=True,
                                            multi="totals"),
        'debit': fields.related('supplier_id',
                                'debit',
                                type='float',
                                string="Debit"),
        'supp_service_days_ids': fields.related('supplier_id',
                                                'supp_service_days_ids',
                                                type='many2many',
                                                relation='week.days',
                                                string="Supplier service \
                                                days"),
        'supp_transport_ids': fields.related('supplier_id',
                                             'supp_transport_ids',
                                             type='one2many',
                                             relation='supplier.transport',
                                             string="Supplier transport"),
        'property_product_pricelist_purchase':
        fields.related('supplier_id',
                       'property_product_pricelist_purchase',
                       type='many2one',
                       relation='product.pricelist',
                       string="Purchase pricelist"),
        'state': fields.selection([('draft', 'Draft'),
                                   ('done', 'Done')], 'State',
                                  readonly=True),
        'purchase_id': fields.many2one('purchase.order', 'Related Purchase',
                                       readonly=True)


    }
    _defaults = {
        'name': lambda obj, cr, uid, context: '/',
        'state': 'draft'
    }

    def create(self, cr, uid, vals, context=None):

        seq_facade = self.pool.get('ir.sequence')
        if vals.get('name', '/') == '/':
            vals['name'] = seq_facade.get(cr,
                                          uid,
                                          'purchase.preorder') or '/'
        return super(purchase_preorder, self).create(cr,
                                                     uid,
                                                     vals,
                                                     context=context)

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def _query_consumptions(self, cr, uid, ids, start, stop,
                            product_id, context=None):
        """
        Query that returns the amount of a product consumed
        between dates
        """
        format_date = start.split(" ")[0].split("-")
        day = format_date[0]
        month = format_date[1]
        year = format_date[2]
        start = year + "-" + month + "-" + day + " " + start.split(" ")[1]
        format_date = stop.split(" ")[0].split("-")
        day = format_date[0]
        month = format_date[1]
        year = format_date[2]
        stop = year + "-" + month + "-" + day + " " + stop.split(" ")[1]
        cr.execute("SELECT sum(s.product_qty) FROM stock_move s \
                    INNER JOIN stock_picking p ON p.id=s.picking_id \
                    INNER JOIN stock_picking_type pt ON \
                    pt.id=p.picking_type_id \
                    WHERE s.state='done' AND pt.code='outgoing' \
                    AND s.product_id=" + str(product_id) + " \
                    AND s.date>='" + start + "' \
                    AND s.date<='" + stop + "'")
        return cr.fetchall()

    def _get_consumptions(self, cr, uid, ids, product_id, context=None):
        """
        Returns: {1: (current, last), 2: (current, last), ... }
        """
        res = {}
        strmonth = ''
        current = 0.0
        previous = 0.0
        prod_fac = self.pool.get('product.product')
        if product_id:
            domain = [('product_tmpl_id', '=', product_id.id)]
            products = prod_fac.search(cr,
                                       uid,
                                       domain)
            if products:
                product = prod_fac.browse(cr, uid, products[0])
            year = int(time.strftime('%Y')) - 1     # Previous year
            ayear = time.strftime('%Y')     # Actual year
            # We go through the months
            for month in range(1, 13):
                # Previous year
                if len(str(month)) == 1:
                    strmonth = '0' + str(month)
                else:
                    strmonth = str(month)
                first_day, last_day = calendar.monthrange(year, month)
                start = '01-' + strmonth + '-' + str(year) + ' 00:00:01'
                d = str(last_day) + '-' + strmonth + '-' + str(year)
                stop = d + ' 23:59:59'
                previous = self._query_consumptions(cr,
                                                    uid,
                                                    ids,
                                                    start,
                                                    stop,
                                                    product.id,
                                                    context)
                if previous[0][0] is None:
                    previous = 0.0
                else:
                    previous = previous[0][0]
                prefirst_day, prelast_day = calendar.monthrange(int(ayear),
                                                                month)
                start = '01-' + strmonth + '-' + ayear + ' 00:00:01'
                d = str(prelast_day) + '-' + strmonth + '-' + ayear
                stop = d + ' 23:59:59'
                current = self._query_consumptions(cr,
                                                   uid,
                                                   ids,
                                                   start,
                                                   stop,
                                                   product.id,
                                                   context)
                if current[0][0] is None:
                    current = 0.0
                else:
                    current = current[0][0]
                res[month] = (current, previous)
        return res

    def _get_products_supplier(self, cr, uid, ids, supplier=False,
                               context=None):
        """
        Function that searches for products you can sell the supplier.
        """
        products = []
        prod_supp_info = self.pool.get('product.supplierinfo')
        if supplier:
            products = prod_supp_info.search(cr,
                                             uid,
                                             [('name', '=', supplier)])
        return products

    def _prepare_prodsupp(self, cr, uid, ids, product=False,
                          supplier=False, context=None):
        """
        Function that fills the data needed to create the lines
        of the supplier's products.
        """
        vals = {}
        purchase_fac = self.pool.get('purchase.order.line')
        # move_fac = self.pool.get('stock.move')
        prod_fac = self.pool.get('product.product')
        if product:
            # Product Data
            products = prod_fac.search(cr,
                                       uid,
                                       [('product_tmpl_id', '=', product.id)])
            if products:
                product = prod_fac.browse(cr, uid, products[0])
                vals = {'product_id': product.id}
                # RSM Data
                # if product.orderpoint_ids:
                #     opoint = product.orderpoint_ids[0]
                # Last Data Purchase
                if supplier:
                    domain = [('order_id.partner_id', '=', supplier.id),
                              ('product_id', '=', product.id),
                              ('order_id.state', '=', 'done')]
                    purlines = purchase_fac.search(cr,
                                                   uid,
                                                   domain,
                                                   order='date_order desc')
                    if purlines:
                        pur = purchase_fac.browse(cr, uid, purlines[0])
                        vals['date_last_purchase'] = pur.date_order
                        vals['qty_last_purchase'] = pur.product_qty
                        vals['price_last_purchase'] = pur.price_unit
                # Data of amounts awaiting of come
                # domain = [('product_id', '=', product.id),
                #           ('partner_id', '=', supplier.id),
                #           ('state', '=', 'assigned'),
                #           ('picking_type_id.code', '=', 'internal')]
                # moves = move_fac.search(cr,
                #                         uid,
                #                         domain,
                #                         order='date_expected desc')
                # if moves:
                #     date = move_fac.browse(cr, uid, moves[0]).date_expected
                #     vals['date_delivery'] = date
                # Data supplier pricelist
                prices = {}
                t_pricelist = self.pool.get('product.pricelist')
                pricelist_id = supplier.property_product_pricelist_purchase.id
                prices = t_pricelist.price_get(cr, uid, [pricelist_id],
                                               product.id, 1, supplier.id,
                                               context=context)
                if prices:
                    vals['list_price'] = prices[pricelist_id]
                    vals['price_purchase'] = prices[pricelist_id]
        return vals

    def _prepare_preorder(self, cr, uid, ids, supplier=False, context=None):
        """
        Function that fill the data needed to create the pre-order
        """
        vals = {}
        if supplier:
            vals['supplier_id'] = supplier.id
        return vals

    def create_preorder(self, cr, uid, ids, undermin_data={}, context=None):
        """
        Function to create the pre-order.
        Returns the view of pre-order filled with all possible data.
        """
        if context is None:
            context = {}
        prodsupp = self.pool.get('products.supplier')
        prosuppinfo = self.pool.get('product.supplierinfo')
        mod_obj = self.pool.get('ir.model.data')
        for data in self.browse(cr, uid, ids, context=context):
            if data.supplier_id:
                sup_id = data.supplier_id
                product_ids = self._get_products_supplier(cr,
                                                          uid,
                                                          ids,
                                                          sup_id.id,
                                                          context)
                # If we find producs, create product lines
                if product_ids:
                    seq = 1
                    for sup in prosuppinfo.browse(cr, uid, product_ids):
                        vals = self._prepare_prodsupp(cr,
                                                      uid,
                                                      ids,
                                                      sup.product_tmpl_id,
                                                      sup.name,
                                                      context=context)
                        supp_prod_uom = sup.product_uom.id
                        if vals:

                            prods_supp = prodsupp.create(cr,
                                                         uid,
                                                         vals,
                                                         context=context)
                            tmp_id = sup.product_tmpl_id
                            consums = self._get_consumptions(cr,
                                                             uid,
                                                             ids,
                                                             tmp_id,
                                                             context)

                            # Rellenamos product_uoc
                            product_uoc_vals = []
                            if sup.base_use_purchase and sup.log_base_id:
                                product_uoc_vals.append(sup.log_base_id.id)
                            if sup.unit_use_purchase and sup.log_unit_id:
                                product_uoc_vals.append(sup.log_unit_id.id)
                            if sup.box_use_purchase and sup.log_box_id:
                                product_uoc_vals.append(sup.log_box_id.id)

                            prodsupp.write(cr,
                                           uid,
                                           prods_supp,
                                           {'preorder_id': data.id,
                                            'sequence': seq,
                                            # 'product_uoc' : product_uoc_vals,
                                            'jan_consu_cur': consums[1][0],
                                            'jan_consu_last': consums[1][1],
                                            'feb_consu_cur': consums[2][0],
                                            'feb_consu_last': consums[2][1],
                                            'mar_consu_cur': consums[3][0],
                                            'mar_consu_last': consums[3][1],
                                            'apr_consu_cur': consums[4][0],
                                            'apr_consu_last': consums[4][1],
                                            'may_consu_cur': consums[5][0],
                                            'may_consu_last': consums[5][1],
                                            'jun_consu_cur': consums[6][0],
                                            'jun_consu_last': consums[6][1],
                                            'jul_consu_cur': consums[7][0],
                                            'jul_consu_last': consums[7][1],
                                            'aug_consu_cur': consums[8][0],
                                            'aug_consu_last': consums[8][1],
                                            'sep_consu_cur': consums[9][0],
                                            'sep_consu_last': consums[9][1],
                                            'oct_consu_cur': consums[10][0],
                                            'oct_consu_last': consums[10][1],
                                            'nov_consu_cur': consums[11][0],
                                            'nov_consu_last': consums[11][1],
                                            'dec_consu_cur': consums[12][0],
                                            'dec_consu_last': consums[12][1],
                                            'product_uoc_qty': 0.0,
                                            'product_uoc': supp_prod_uom
                                            },
                                           context=context)
                            seq += 1
                # From under minimum model
                if undermin_data:
                    for product_id in undermin_data:
                        min_proposal = undermin_data[product_id]
                        l = prodsupp.search(cr,
                                            uid,
                                            [('preorder_id', '=', data.id),
                                             ('product_id', '=', product_id)])
                        if l:
                            line = prodsupp.browse(cr, uid, l[0],
                                                   context={'tm': True})
                            line.write({'product_uoc_qty': min_proposal})
                            line._check_uoc_qty()

        form_res = mod_obj.get_object_reference(cr,
                                                uid,
                                                'purchase_preorder',
                                                'purchase_preorder_form')
        form_id = form_res and form_res[1] or False
        tree_res = mod_obj.get_object_reference(cr,
                                                uid,
                                                'purchase_preorder',
                                                'view_purchase_preorder_tree')
        tree_id = tree_res and tree_res[1] or False

        value = {
            'name': 'Pre Order',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'view_id': False,
            'res_model': 'purchase.preorder',
            'type': 'ir.actions.act_window',
            'create': False,
            'res_id': data.id,
            'views': [(form_id, 'form'), (tree_id, 'tree')]}
        return value

    def generate_purchase_order(self, cr, uid, ids, context=None):
        """
        Generate a purchase order from the data pre-order.
        """
        if context is None:
            context = {}
        vals = {}
        valspartner = {}
        purchase = self.pool.get('purchase.order')
        pline = self.pool.get('purchase.order.line')
        acc_pos_obj = self.pool.get('account.fiscal.position')
        seq_obj = self.pool.get('ir.sequence')
        user = self.pool.get('res.users')
        warehouse = self.pool.get('stock.warehouse')
        new_id = False
        warehouse_id = False
        for pre in self.browse(cr, uid, ids):
            pricelist = pre.supplier_id.property_product_pricelist_purchase.id
            pname = seq_obj.get(cr, uid, 'purchase.order') or 'PO: PreOrder'
            fiscal_posion = pre.supplier_id.property_account_position and \
                pre.supplier_id.property_account_position.id or \
                False
            payment = pre.supplier_id.property_supplier_payment_term.id \
                or False
            date_order = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            company = user.browse(cr, uid, uid).company_id.id
            warehouses = warehouse.search(cr,
                                          uid,
                                          [('company_id', '=', company)])
            if warehouses:
                warehouse_id = warehouse.browse(cr, uid, warehouses[0])
            location = warehouse_id and warehouse_id.wh_input_stock_loc_id.id \
                or False
            vals = {'partner_id': pre.supplier_id.id,
                    'pricelist_id': pricelist,
                    'location_id': location,
                    'name': pname,
                    'origin': 'PreOrder',
                    'warehouse_id': warehouse_id and warehouse_id.id or False,
                    'date_order': date_order,
                    'company_id': company,
                    'fiscal_position': fiscal_posion,
                    'payment_term_id': payment,
                    'state': 'draft',
                    'preorder_id': pre.id}
            valspartner = purchase.onchange_partner_id(cr,
                                                       uid,
                                                       ids,
                                                       pre.supplier_id.id)
            if valspartner:
                if valspartner['value'].get('payment_term_id', False):
                    payment_term = valspartner['value']['payment_term_id']
                    vals['payment_term_id'] = payment_term
                if valspartner['value'].get('fiscal_position', False):
                    fiscal_position = valspartner['value']['fiscal_position']
                    vals['fiscal_position'] = fiscal_position
                if valspartner['value'].get('pricelist_id', False):
                    pricelist_id = valspartner['value']['pricelist_id']
                    vals['pricelist_id'] = pricelist_id
            new_id = purchase.create(cr, uid, vals)
            pre.write({'state': 'done', 'purchase_id': new_id})
            if pre.product_supplier_ids:
                for line in pre.product_supplier_ids:
                    if line.product_uoc_qty:
                        taxes_ids = line.product_id.supplier_taxes_id
                        acc_posi = pre.supplier_id.property_account_position
                        taxes = acc_pos_obj.map_tax(cr,
                                                    uid,
                                                    acc_posi,
                                                    taxes_ids)


                        lname = line.product_id.partner_ref
                        if line.product_id.description_purchase:
                            lname += '\n' + \
                                line.product_id.description_purchase
                        #import pdb; pdb.set_trace()
                        seller_delay = int(line.product_id.seller_delay)
                        format = DEFAULT_SERVER_DATETIME_FORMAT
                        dateo = datetime.strptime(date_order, format)
                        ldate = dateo + relativedelta(days=seller_delay)

                        #supp = self.pool.get('product.supplierinfo')
                        #suppinfo_ids = supp.search(cr, uid, [('product_tmpl_id','=',line.product_id.id),('name','=', line.preorder_id.supplier_id.id)])
                        #suppinfo = supp.browse(cr, uid, suppinfo_ids)
                        #lname = (suppinfo.product_code and ('['+ suppinfo.product_code +'] ') or '') + (suppinfo.product_name or '')
                        product_pool = self.pool.get('product.product')
                        lname = product_pool.get_product_supplier_name(cr, uid, line.preorder_id.supplier_id.id,line.product_id.id)
                        values_line = {'product_id': line.product_id.id,
                                      'name': lname,
                                      #'product_qty': line.unitskg, Creo que es product_qty
                                      'product_qty' : line.product_qty,
                                      'product_uoc_qty' :line.product_uoc_qty,
                                      # 'boxes': line.boxes,
                                      # 'mantles': line.mantles,
                                      # 'palets': line.palets,
                                      'product_uom': line.product_id.uom_id.id,
                                      'product_uoc': line.product_uoc.id,
                                      'price_unit' : line.product_id.standard_price,
                                      'price_udc': line.price_purchase,
                                      'order_id': new_id,
                                      'date_planned': ldate,
                                      'discount': line.precentage_promo,
                                      'taxes_id': [(6, 0, taxes)]}

                        pline.create(cr, uid, values_line)


        value = {'domain': str([('id', 'in', [new_id])]),
                 'view_type': 'form',
                 'view_mode': 'tree,form',
                 'res_model': 'purchase.order',
                 'view_id': False,
                 'type': 'ir.actions.act_window',
                 'res_id': new_id}
        return value

    def open_in_tree(self, cr, uid, ids, context=None):


        #import pdb; pdb.set_trace()
        view_ref = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'purchase_preorder', 'product_supplier_preorder_tree_full')


        tree_res = view_ref and view_ref[1] or False,


        pool_ids = self.browse (cr, uid,ids, context).product_supplier_ids
        #'view_id = 'product_supplier_preorder_tree_full'
        preorder_id = self.browse(cr, uid, ids).id
        res = {
            'type': 'ir.actions.act_window',
            'name': 'Products Supplier',
            'view_mode': 'form, tree',
            'view_type': 'form',
            'view_id': tree_res,
            'views' :[(tree_res, 'tree'), (False, 'form')],
            'res_model': 'products.supplier',
            'context': context,
            'domain' : [['preorder_id', '=', preorder_id]] #pool_ids[0].preorder_id.id]]
        }


        return res


class products_supplier(osv.Model):
    _name = 'products.supplier'
    _description = 'Products Supplier'
    _order = "id desc"


    def _amount_subtotal(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for prod in self.browse(cr, uid, ids, context=context):
            res[prod.id] = 0.0
            if prod.price_purchase and prod.product_uoc_qty:
                res[prod.id] = prod.price_purchase * prod.product_uoc_qty
        return res

    def _get_min_qty_supplier(self, cr, uid, ids, fields_name, args,
                              context=None):

        res = {}
        supp_info_obj = self.pool.get('product.supplierinfo')
        for obj in self.browse(cr, uid, ids, context):
            res[obj.id] = {
                'min_qty': 0.0,
                'min_mantles': 0.0,
                'min_palets': 0.0,
            }
            supp_info_ids = supp_info_obj.search(cr, uid,
                                                 [('product_tmpl_id', '=',
                                                   obj.product_id.id),
                                                  ('name', '=',
                                                   obj.preorder_id
                                                   .supplier_id.id)],
                                                 context=context)
            if supp_info_ids:
                info_obj = supp_info_obj.browse(cr, uid, supp_info_ids[0],
                                                context)
                prod_qty = info_obj.min_qty
                res[obj.id]['min_qty'] = prod_qty
                un_ca = info_obj.supp_un_ca
                ca_ma = info_obj.supp_ca_ma
                ma_pa = info_obj.supp_ma_pa

                uom = info_obj.product_tmpl_id.uom_id
                product = self.pool.get('product.product')
                product_id = product.browse(cr, uid,
                                            [info_obj.product_tmpl_id.id])
                prod_qty = \
                    (prod_qty *
                        product_id._conv_units(uom.id,
                                               info_obj.log_box_id.id,
                                               info_obj.name.id)) or 1.0
                boxes = round(prod_qty or 0.0, 2)
                mantles = round(ca_ma and (boxes / ca_ma) or 0.0, 2)
                palets = round(ma_pa and (mantles / ma_pa) or 0.0, 2)
                res[obj.id]['min_mantles'] = mantles
                res[obj.id]['min_palets'] = palets

        return res

    _columns = {
        'preorder_id': fields.many2one('purchase.preorder',
                                       'Purchase PreOrder'),

        'product_id': fields.many2one('product.product',
                                      'Product',
                                      required=True),
        'product_state': fields.related('product_id',
                                        'state2',
                                        type='selection',
                                        selection=PRODUCT_STATE_SELECTION,
                                        string="State"),
        'min_fixed': fields.float('Min. Fixed'),  # TODO eliminar, sin función
        'incoming_qty': fields.related('product_id',
                                       'incoming_qty',
                                       type='float',
                                       string='Incoming qty.',
                                       help='Quantity pending to recive'),
        # 'date_delivery': fields.date('Date Delivery'),
        'real_stock': fields.related('product_id', 'qty_available',
                                     type='float',
                                     string='Real Stock',
                                     readonly=True,
                                     help='Quantity in stock'),
        'virtual_stock': fields.related('product_id',
                                        'virtual_stock_conservative',
                                        type='float',
                                        string='Virtual Stock Conservative',
                                        readonly=True,
                                        help='Real stock - outgoings '),
        'virtual_available': fields.related('product_id',
                                            'virtual_available',
                                            type='float',
                                            string='Quantity available',
                                            readonly=True,
                                            help='Real stock + incomings - '
                                            'outgongs'),
        'sequence': fields.integer('Sequence'),
        'date_last_purchase': fields.date('Date'),
        'qty_last_purchase': fields.float('Qty.'),
        'price_last_purchase': fields.float('Price'),
        'list_price': fields.float('List Price'),
        'price_purchase': fields.float('Price purchase'),
        'subtotal': fields.function(_amount_subtotal,
                                    type="float",
                                    string='Amount',
                                    readonly=True),
        'palets': fields.float('Palets'),
        'mantles': fields.float('Mantles'),
        'boxes': fields.float('Boxes'),
        'unitskg': fields.float('Unit or Kg'),
        'jan_consu_cur': fields.float('Jan Consu Cur'),
        'jan_consu_last': fields.float('Jan Consu Last'),
        'feb_consu_cur': fields.float('Feb Consu Cur'),
        'feb_consu_last': fields.float('Feb Consu Last'),
        'mar_consu_cur': fields.float('Mar Consu Cur'),
        'mar_consu_last': fields.float('Mar Consu Last'),
        'apr_consu_cur': fields.float('Apr Consu Cur'),
        'apr_consu_last': fields.float('Apr Consu Last'),
        'may_consu_cur': fields.float('May Consu Cur'),
        'may_consu_last': fields.float('May Consu Last'),
        'jun_consu_cur': fields.float('Jun Consu Cur'),
        'jun_consu_last': fields.float('Jun Consu Last'),
        'jul_consu_cur': fields.float('Jul Consu Cur'),
        'jul_consu_last': fields.float('Jul Consu Last'),
        'aug_consu_cur': fields.float('Aug Consu Cur'),
        'aug_consu_last': fields.float('Aug Consu Last'),
        'sep_consu_cur': fields.float('Sep Consu Cur'),
        'sep_consu_last': fields.float('Sep Consu Last'),
        'oct_consu_cur': fields.float('Oct Consu Cur'),
        'oct_consu_last': fields.float('Oct Consu Last'),
        'nov_consu_cur': fields.float('Nov Consu Cur'),
        'nov_consu_last': fields.float('Nov Consu Last'),
        'dec_consu_cur': fields.float('Dec Consu Cur'),
        'dec_consu_last': fields.float('Dec Consu Last'),
        'min_qty': fields.function(_get_min_qty_supplier,
                                   type='float', string="Min quantity",
                                   multi="min_qty", readonly=True),
        'min_mantles': fields.function(_get_min_qty_supplier,
                                       type='float', string="Min mantles",
                                       readonly=True),
        'min_palets': fields.function(_get_min_qty_supplier,
                                      type='float', string="Min palets",
                                      multi="min_qty", readonly=True),
        'stock_days': fields.related('product_id', 'remaining_days_sale',
                                     type='float',
                                     readonly=True,
                                     string='Stock Days'),
        'net_cost': fields.float('Net cost'),
        'do_onchange': fields.boolean('Do Onchange'),
        'net_net_cost': fields.float('Net net cost'),
        'service_days_ids': fields.related('preorder_id',
                                           'supp_service_days_ids',
                                           type='many2many',
                                           relation='week.days',
                                           string="Service Days"),
        'supplier_delay': fields.related('product_id',
                                         'seller_ids',
                                         'delay',
                                         type='integer',
                                         string="Delivery Time")
    }

    def update_price(self, cr, uid, ids, context=None):
        prod_obj = self.pool.get('product.product')
        for obj in self.browse(cr, uid, ids, context):
            if obj.product_id.standard_price != obj.price_purchase:
                prod_obj.write(cr, uid, obj.product_id.id,
                               {'standard_price': obj.price_purchase})
        return True

    def open_in_form(self, cr, uid, ids, context=None):
        view_ref = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'purchase_preorder', 'product_supplier_preorder_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products Supplier',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id,
            'res_model': 'products.supplier',
            'nodestroy': True,
            'res_id': ids[0],  # assuming the many2one
            'target': 'new',
            'context': context,
        }


class productsSupplier(models.Model):
    _inherit = 'products.supplier'

    @api.one
    def _calc_security_days(self):
        op_t = self.env['stock.warehouse.orderpoint']
        security_days = 0.00
        domain = [
            ('product_id', '=', self.product_id.id),
            ('min_days_id', '!=', False)
        ]
        op_objs = op_t.search(domain)
        if op_objs:
            security_days = op_objs[0].min_days_id.days_sale
        self.security_days = security_days

    @api.one
    def _calc_delivery_date(self):
        """
        Get delivery date same way that in purchase order line
        """
        date = False
        pol = self.env['purchase.order.line']
        if self.product_id.seller_ids:
            today = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            date = pol._get_date_planned(self.product_id.seller_ids[0], today)
            if date:
                date = date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.delivery_date = date

    # En español porque no coje la traducción en otra clase con la nueva api
    security_days = fields2.Float('Días stock seguridad', readonly=True,
                                  compute='_calc_security_days',
                                  help="Días de stock de seguridad del "
                                  "producto configurados en una regla de "
                                  "reabastecimiento")
    delivery_date = fields2.Date('Fecha de Entrega', readonly=True,
                                 compute='_calc_delivery_date',
                                 help="Fecha de entrega estimada")
