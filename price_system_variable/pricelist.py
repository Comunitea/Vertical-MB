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
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import tools
from lxml import etree
import time

# ****************************************************************************
# ************************PRICELIST MODEL OVERWRITES**************************
# ****************************************************************************


class product_pricelist_item(osv.Model):
    def _price_field_get(self, cr, uid, context=None):
        """
        We overwrites this method to add a new rules based type:
        Variable Price: For fresh products (sale pricelist)
        Supplier Price Change: For no fresh products (purchase pricelist)
        PVP product change: For no fresh products (sale pricelist)
        """
        if context is None:
            context = {}
        pt = self.pool.get('product.price.type')
        ids = pt.search(cr, uid, [], context=context)
        result = []
        for line in pt.browse(cr, uid, ids, context=context):
            result.append((line.id, line.name))
        result.append((-1, _('Other Pricelist')))
        result.append((-2, _('Supplier Prices on the product form')))
        result.append((-3, _('Variable Price')))
        result.append((-4, _('Supplier Price Change')))
        result.append((-5, _('PVP product Change')))
        return result

    _inherit = "product.pricelist.item"
    _columns = {
        'base': fields.selection(_price_field_get, 'Based on', required=True,
                                 size=-1, help="Base price for computation."),
    }


class product_pricelist(osv.Model):
    _inherit = 'product.pricelist'

    def _get_pricelist_based_in_x(self, cr, uid, x):
        """
        Return a list of product pricelist ids which rules based in:
        x = -3 Change Variable price
        x = -4 Change Supplier costs
        x = -5 Change product pvp
        All returned pricelist are sale type
        """
        rule_pool = self.pool.get("product.pricelist.item")
        rule_ids = rule_pool.search(cr, uid, [('base', '=', x)])
        pricelist_ids = set()
        for rule in rule_pool.browse(cr, uid, rule_ids):
            pricelist_obj = rule.price_version_id.pricelist_id
            if pricelist_obj.type == 'sale':
                pricelist_ids.add(pricelist_obj.id)
        return list(pricelist_ids)

    def _get_supplier_price(self, cr, uid, supplier_id, product_id):
        """
        Custom method that search in change_supplier_cost lines and look for
        one matching with a parent model in updated state and whitch date be
        the most recently.
        @return: a list with cost and supplier code definmed in the model.
        """
        price_code = [0.0, False]  # [cost, supplier_code]
        shl = self.pool.get("supplier.change.line")
        domain = [('change_id.partner_id', '=', supplier_id),
                  ('change_id.state', '=', 'updated'),
                  ('product_id', '=', product_id),
                  ('date', '<=', time.strftime('%Y-%m-%d'))
                  ]
        line_ids = shl.search(cr, uid, domain, limit=1, order='date desc')
        if not line_ids:  # No matched line in change supplier costs model
            return ["warn", False]  # For raise a warning in purchase onchange
        line = shl.browse(cr, uid, line_ids[0])
        price_code[0] = line.new_cost
        price_code[1] = line.sup_code or False
        return price_code

    def _get_product_pvp(self, cr, uid, product_id, pricelist_id):
        """
        Custom method that search in change_product_pvp lines and look for
        one matching with a parent model in updated state and with a date
        range containeng the current date
        @return: a list with pvp and min_price defined in the model.
        """
        price_and_min = [0.0, 0.0]  # [price, min_price]
        pvp_line = self.pool.get("pricelist.pvp.line")
        domain = [('change_id.product_id', '=', product_id),
                  ('change_id.state', '=', 'updated'),
                  ('pricelist_id', '=', pricelist_id),
                  ('date_start', '<=', time.strftime('%Y-%m-%d')),
                  ('date_end', '>=', time.strftime('%Y-%m-%d'))]
        line_ids = pvp_line.search(cr, uid, domain, limit=1, order='id desc')
        if not line_ids:
            return ["warn", 0.0]
        line = pvp_line.browse(cr, uid, line_ids[0])
        price_and_min[0] = line.pvp
        price_and_min[1] = line.min_price
        return price_and_min

    def ts_get_product_pvp(self, cr, uid, product_id, pricelist_id):
        """
        Copy of last method. Only called from telesale module.
        Custom method that search in change_product_pvp lines and look for
        one matching with a parent model in updated state and with a date
        range containeng the current date
        @return: a list with pvp and min_price defined in the model.
        """
        price_and_min = [0.0, 0.0]  # [price, min_price]
        pvp_line = self.pool.get("pricelist.pvp.line")
        domain = [('change_id.product_id', '=', product_id),
                  ('change_id.state', '=', 'updated'),
                  ('pricelist_id', '=', pricelist_id),
                  ('date_start', '<=', time.strftime('%Y-%m-%d')),
                  ('date_end', '>=', time.strftime('%Y-%m-%d'))]
        line_ids = pvp_line.search(cr, uid, domain, limit=1, order='id desc')
        if not line_ids:
            return ["warn", 0.0]
        line = pvp_line.browse(cr, uid, line_ids[0])
        price_and_min[0] = line.pvp
        price_and_min[1] = line.min_price
        return price_and_min

    def price_get_multi(self, cr, uid, pricelist_ids, products_by_qty_by_partner, context=None):
        """multi products 'price_get'.
           @param pricelist_ids:
           @param products_by_qty:
           @param partner:
           @param context: {
             'date': Date of the pricelist (%Y-%m-%d),}
           @return: a dict of dict with product_id as key and a dict 'price by pricelist' as value
        """
        if not pricelist_ids:
            pricelist_ids = self.pool.get('product.pricelist').search(cr, uid, [], context=context)
        results = {}
        for pricelist in self.browse(cr, uid, pricelist_ids, context=context):
            subres = self._price_get_multi(cr, uid, pricelist, products_by_qty_by_partner, context=context)
            for product_id,price in subres.items():
                results.setdefault(product_id, {})
                if  type(price) == list:
                    results[product_id][pricelist.id] = price[0]
                    results[product_id]['item_id'] = price[1]
                else:
                    results[product_id][pricelist.id] = price
        return results

    def _price_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        context = context or {}
        date = context.get('date') or time.strftime('%Y-%m-%d')

        products = map(lambda x: x[0], products_by_qty_by_partner)
        currency_obj = self.pool.get('res.currency')
        product_obj = self.pool.get('product.template')
        product_uom_obj = self.pool.get('product.uom')
        price_type_obj = self.pool.get('product.price.type')

        if not products:
            return {}
        
        version = False
        for v in pricelist.version_id:
            if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
                version = v
                break
        if not version:
            raise osv.except_osv(_('Warning!'), _("At least one pricelist has no active version !\nPlease create or activate one."))
        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = categ_ids.keys()

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            prod_ids = [product.id for product in tmpl.product_variant_ids for tmpl in products]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        # Load all rules
        cr.execute(
            'SELECT i.id '
            'FROM product_pricelist_item AS i '
            'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s)) '
                'AND (product_id IS NULL OR (product_id = any(%s))) '
                'AND ((categ_id IS NULL) OR (categ_id = any(%s))) '
                'AND (price_version_id = %s) '
            'ORDER BY sequence, min_quantity desc',
            (prod_tmpl_ids, prod_ids, categ_ids, version.id))
        
        item_ids = [x[0] for x in cr.fetchall()]
        items = self.pool.get('product.pricelist.item').browse(cr, uid, item_ids, context=context)

        price_types = {}

        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            uom_price_already_computed = False
            results[product.id] = 0.0
            price = False
            custom_way = False
            for rule in items:
                if rule.min_quantity and qty<rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id<>rule.product_tmpl_id.id:
                        continue
                    if rule.product_id:
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id<>rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id<>rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.base == -1:
                    if rule.base_pricelist_id:
                        price_tmp = self._price_get_multi(cr, uid,
                                rule.base_pricelist_id, [(product,
                                qty, False)], context=context)[product.id]
                        ptype_src = rule.base_pricelist_id.currency_id.id
                        uom_price_already_computed = True
                        price = currency_obj.compute(cr, uid,
                                ptype_src, pricelist.currency_id.id,
                                price_tmp, round=False,
                                context=context)
                elif rule.base == -2:
                    for seller in product.seller_ids:
                        if (not partner) or (seller.name.id<>partner):
                            continue
                        qty_in_seller_uom = qty
                        from_uom = context.get('uom') or product.uom_id.id
                        seller_uom = seller.product_uom and seller.product_uom.id or False
                        if seller_uom and from_uom and from_uom != seller_uom:
                            qty_in_seller_uom = product_uom_obj._compute_qty(cr, uid, from_uom, qty, to_uom_id=seller_uom)
                        else:
                            uom_price_already_computed = True
                        for line in seller.pricelist_ids:
                            if line.min_quantity <= qty_in_seller_uom:
                                price = line.price

                # BASED ON VARIABLE PRICE
                elif rule.base == -3:
                    price = -1  # price when we sale fresh products
                    custom_way = True
                    price = [price, rule.id] #put itm_id

                # BASED ON CHANGE_SUPPLIER_COST MODEL
                elif rule.base == -4:
                    price_cod = self._get_supplier_price(cr, uid,
                                                         partner,
                                                         product.id)
                    # we are going to return a list with cost and
                    # supplier code to cath then in the purchase
                    # product onchange
                    price = price_cod
                    custom_way = True
                    price = [price, rule.id] #put itm_id

                # BASED ON CHANGE_PRODUCT_PVP MODEL
                elif rule.base == -5:
                    price = self._get_product_pvp(cr, uid, product.id,
                                                  pricelist.id)[0]
                    custom_way = True
                    price = [price, rule.id] #put itm_id

                else:
                    if rule.base not in price_types:
                        price_types[rule.base] = price_type_obj.browse(cr, uid, int(rule.base))
                    price_type = price_types[rule.base]

                    uom_price_already_computed = True
                    price = currency_obj.compute(cr, uid,
                            price_type.currency_id.id, pricelist.currency_id.id,
                            product_obj._price_get(cr, uid, [product],
                            price_type.field, context=context)[product.id], round=False, context=context)

                if price is not False and not custom_way:
                    price_limit = price
                    price = price * (1.0+(rule.price_discount or 0.0))
                    if rule.price_round:
                        price = tools.float_round(price, precision_rounding=rule.price_round)
                    price += (rule.price_surcharge or 0.0)
                    if rule.price_min_margin:
                        price = max(price, price_limit+rule.price_min_margin)
                    if rule.price_max_margin:
                        price = min(price, price_limit+rule.price_max_margin)
                break

            if price and not custom_way:
                if 'uom' in context and not uom_price_already_computed:
                    uom = product.uos_id or product.uom_id
                    price = product_uom_obj._compute_price(cr, uid, uom.id, price, context['uom'])

            results[product.id] = price
        return results

# ****************************************************************************
# ********************** VARIABLE PRICELIST MODEL*****************************
# ****************************************************************************


class variable_pricelist(osv.Model):
    _name = "variable.pricelist"
    _order = "sequence"
    _columns = {
        'name': fields.char('Name', size=128, required="True"),
        'sequence': fields.integer('Sequence', required=True),
        'product_id': fields.many2one('product.product', 'Product',
                                      domain=[('product_class', '=',
                                               'fresh')]),
        'categ_id': fields.many2one('product.category', 'Product Category'),
        'range_ids': fields.one2many('pricelist.range', 'var_pricelist_id',
                                     'Ranges table')
    }

    def _add_margin_fields(self, cr, uid, res, pricelist_ids, context=None):
        """ Add many margin fields as pricelist in pricelist_ids"""
        if context is None:
            context = {}
        pricelist_pool = self.pool.get("product.pricelist")
        field_dic = {}
        for pri_list in pricelist_pool.browse(cr, uid, pricelist_ids, context):
            field_dic.update({str(pri_list.id): {'digits': (16, 2),
                                                 'required': True,
                                                 'selectable': True,
                                                 'string': pri_list.name,
                                                 'type': 'float',
                                                 'views': {}}})
        res['fields']['range_ids']['views']['tree']['fields'].update(field_dic)
        return res

    def _check_rec(self, eview, value, str_to_add):
            """busca recursivamente en el arch del xml el atributo domain con
               un valor dado y lo sustituye por un nuevo valor"""
            if eview.attrib.get('name', False) == value:
                eview.addnext(etree.fromstring(str_to_add))
            for child in eview:
                self._check_rec(child, value, str_to_add)
            return False

    def _generate_view(self, cr, uid, res, pricelist_ids):
        """Creates the columns of margin table"""
        pricelist_pool = self.pool.get("product.pricelist")
        eview = etree.fromstring(res['fields']['range_ids']['views']['tree']
                                 ['arch'])
        field_name = 'security_margin'
        for pricelist in pricelist_pool.browse(cr, uid, pricelist_ids):
            xml_code = u"""<field name="%s"/>""" % str(pricelist.id)
            self._check_rec(eview, field_name, xml_code)
            field_name = str(pricelist.id)
        e = eview
        res['fields']['range_ids']['views']['tree']['arch'] = etree.tostring(e)
        return res

    def fields_view_get(self, cr, user, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        """
        Overwrite in order to get the margin table dinamically.
        """
        res = super(variable_pricelist, self).fields_view_get(cr, user,
                                                              view_id,
                                                              view_type,
                                                              context,
                                                              toolbar=toolbar,
                                                              submenu=submenu)
        t_plist = self.pool.get("product.pricelist")
        if context is None:
            context = {}
        if res['type'] == 'form':
            pricelist_ids = t_plist._get_pricelist_based_in_x(cr, user, '-3')
            res = self._add_margin_fields(cr, user, res, pricelist_ids,
                                          context)
            res = self._generate_view(cr, user, res, pricelist_ids)
        return res

    def update_taxes(self, cr, uid, ids, context):
        """????"""
        if context is None:
            context = {}
        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference(cr, uid, 'price_system_variable',
                                            'action_variable_pricelist')
        action = self.pool.get(res[0]).read(cr, uid, res[1],
                                            context=context)
        action['view_mode'] = 'form'
        return action


class pricelist_range(osv.Model):
    _name = "pricelist.range"
    _order = "from_cost"
    _columns = {
        'var_pricelist_id': fields.many2one('variable.pricelist',
                                            'Variable Pricelist',
                                            ondelete='cascade'),
        'from_cost': fields.float('From Cost', required=True,
                                  digits_compute=
                                  dp.get_precision('Product Cost')),
        'to_cost': fields.float('To Cost', required=True,
                                digits_compute=
                                dp.get_precision('Product Cost')),
        'security_margin': fields.float('Security Margin', required=True,
                                        digits_compute=
                                        dp.get_precision('Product Price')),
        'margin_ids': fields.one2many('pricelist.margin', 'range_id',
                                      'Margins table'),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        res = super(pricelist_range, self).write(cr, uid, ids, vals,
                                                 context=context)
        t_margin = self.pool.get("pricelist.margin")
        for key in vals:
            if key not in ['from_cost', 'to_cost', 'security_margin',
                           'var_pricelist_id']:
                domain = [('range_id', '=', ids[0]),
                          ('pricelist_id', '=', int(key))]
                margin_id = t_margin.search(cr, uid, domain, context=context)
                if margin_id:
                    vals2 = {'margin': vals[key]}
                    t_margin.write(cr, uid, margin_id, vals2, context=context)
                else:
                    vals2 = {'margin': vals[key], 'range_id': ids[0],
                             'pricelist_id': int(key)}
                    t_margin.create(cr, uid, vals2, context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        res = super(pricelist_range, self).create(cr, uid, vals,
                                                  context=context)

        t_margin = self.pool.get("pricelist.margin")
        for key in vals:
            if key not in ['from_cost', 'to_cost', 'security_margin',
                           'var_pricelist_id']:
                vals2 = {
                    'range_id': res,
                    'pricelist_id': int(key),
                    'margin': vals[key]
                }
                t_margin.create(cr, uid, vals2, context=context)
        return res

    def read(self, cr, uid, ids, fields=None, context=None,
             load='_classic_read'):
        if context is None:
            context = {}
        res = super(pricelist_range, self).read(cr, uid, ids, fields=fields,
                                                context=context, load=load)
        t_margin = self.pool.get("pricelist.margin")
        for rang in res:
            domain = [('range_id', '=', rang['id'])]
            margin_ids = t_margin.search(cr, uid, domain, context=context)
            res2 = t_margin.read(cr, uid, margin_ids,
                                 ['margin', 'pricelist_id'],
                                 context=context, load=load)
            for margin in res2:
                key = str(margin['pricelist_id'])
                if type(margin['pricelist_id']) == tuple:
                    key = str(margin['pricelist_id'][0])
                rang.update({key: margin['margin']})
        return res


class pricelist_margin(osv.Model):
    """
    Last part of Margin table.It defines a margin for a pricelist column
    """
    _name = "pricelist.margin"
    _order = "pricelist_id"
    _columns = {
        'range_id': fields.many2one('pricelist.range', 'Range',
                                    ondelete='cascade'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
                                        domain=[('type', '=', 'sale')]),
        'margin': fields.float('Margin', required=True,
                               digits_compute=
                               dp.get_precision('Product Price')),
    }

    def _check_margins(self, cr, uid, ids, context=None):
        """
        Check margin values. If margin is negative or 100
        raises an error
        """
        if context is None:
            context = {}
        for pm in self.browse(cr, uid, ids, context):
            if pm.margin < 0 or pm.margin >= 100:
                return False
        return True

    _constraints = [
        (_check_margins,
         'Margin must be less than 100% and can not be negative.',
         ['margin'])
    ]

# ****************************************************************************
# ********************** CHANGE VARIABLE PRICELIST MODEL***********************
# ****************************************************************************


class change_variable_pricelist(osv.Model):
    """
    This model is generated when a purchase order marked as update
    pricelist is confirmed.
    """
    _name = 'change.variable.pricelist'
    _order = 'date desc'
    _columns = {
        'name': fields.char('Name', size=256),
        'date': fields.datetime('Date', readonly=True, required=True),
        'product_id': fields.many2one('product.product', 'Product',
                                      readonly=True, required=True,
                                      domain=[('product_class', '=',
                                               'fresh')]),
        'change_line_ids': fields.one2many('variable.change.line',
                                           'change_id', 'Variable pricelist'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('updated', 'Updated')], 'Status',
                                  required=True, readonly=True),
        'purchase_id': fields.many2one('purchase.order', 'Orig Purchase',
                                       readonly=True),
        'label': fields.boolean('Print label?'),
        'note': fields.text('Observations', readonly=True)
    }
    _defaults = {
        'state': 'draft'
    }

    def update_sale_prices(self, cr, uid, ids, context=None):
        """
        Search sale order lines marked as to update and updates
        price_unit of sale order lines
        """
        if context is None:
            context = {}
        t_line = self.pool.get('sale.order.line')
        for cvp in self.browse(cr, uid, ids, context=context):
            domain = [('to_update', '=', True),
                      ('product_id', '=', cvp.product_id.id)]
            sol_ids = t_line.search(cr, uid, domain, context=context)
            for sol in t_line.browse(cr, uid, sol_ids, context=context):
                for ch_line in cvp.change_line_ids:
                    if sol.order_id.pricelist_id.id == ch_line.pricelist_id.id:
                        sol.write({'price_unit': ch_line.current_pvp,
                                   'state': 'confirmed',
                                   'change_id': cvp.id,
                                   'to_update': False})
            cvp.write({'state': 'updated'})
        return

    def get_prices_back(self, cr, uid, ids, context=None):
        """
        When you cancel the model of change_variable_pricelist this
        functions get price units of sale order lines back (to -1.00)
        an madrked as to_update
        """
        if context is None:
            context = {}
        t_line = self.pool.get('sale.order.line')
        for cvp in self.browse(cr, uid, ids, context=context):
            domain = [('change_id', '=', cvp.id),
                      ('to_update', '=', False)]
            sol_ids = t_line.search(cr, uid, domain, context=context)
            t_line.write(cr, uid, sol_ids, {'price_unit': -1,
                                            'to_update': True,
                                            'change_id': False})
            cvp.write({'state': 'draft'})


class variable_change_line(osv.Model):
    """
    This model are lines of change_variable_pricelist model.
    It defines the new prices for each pricelist
    """
    _name = 'variable.change.line'
    _order = 'pricelist_id'
    _columns = {
        'change_id': fields.many2one('change.variable.pricelist',
                                     'Change Variable pricelist',
                                     ondelete='cascade'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
                                        domain=[('type', '=', 'sale')]),
        'previous_cost': fields.float('Previous cost', required=True,
                                      digits_compute=
                                      dp.get_precision('Product Cost'),
                                      readonly=True),
        'current_cost': fields.float('Current cost', required=True,
                                     digits_compute=
                                     dp.get_precision('Product Cost'),
                                     readonly=True),
        'real_margin': fields.float('Real Margin', required=True,
                                    digits_compute=
                                    dp.get_precision('Product Price'),
                                    readonly=True),
        'previous_pvp': fields.float('Previous PVP', required=True,
                                     digits_compute=
                                     dp.get_precision('Product Price'),
                                     readonly=True),
        'current_pvp': fields.float('Current PVP', required=True,
                                    digits_compute=
                                    dp.get_precision('Product Price')),
    }


# ****************************************************************************
# **************************CHANGE SUPPLIER COSTS*****************************
# ****************************************************************************


class change_supplier_cost(osv.Model):
    """
    Model to change suppliers costs. When we do a purchase order with a
    supplier and a pricelist with a rule based on 'Supplier Price Change'
    (base: -4) we search into this model
    """
    _name = 'change.supplier.cost'
    _columns = {
        'state': fields.selection([('draft', 'Draft'),
                                   ('updated', 'Updated')], 'Status',
                                  required=True, readonly=True),
        'name': fields.char('Name', size=256, required=True),
        'date': fields.datetime('Date', required=True),
        'partner_id': fields.many2one('res.partner', 'Supplier',
                                      required=True,
                                      domain=[('supplier', '=', True)]),
        'line_ids': fields.one2many('supplier.change.line',
                                    'change_id', 'Change supplier prices'),
    }
    _defaults = {
        'state': 'draft',
        'date': time.strftime("%Y-%m-%d %H:%M:%S")
    }

    def update_prices(self, cr, uid, ids, context=None):
        """
        Button method to change to updated state in order to be considered
        when we search into this model
        """
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'state': 'updated'}, context=context)

    def get_prices_back(self, cr, uid, ids, context=None):
        """
        Button method to get back ti draft state in order to be considered
        when we search into this model.
        """
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        return


class supplier_change_line(osv.Model):
    """
    This model are lines of change_supplier_cost model.
    It defines the new costs for each product and the supplier code to be
    showed in purchase order line.
    Products must be no fresh.
    """
    _name = 'supplier.change.line'
    _order = 'product_id'

    def _get_fields(self, cr, uid, ids, field_name, args, context=None):
        """
        Calculates all readonly function fields again, appart of onchange
        methods becaouse we can not write in model readonly fields so we
        recalcule them each time we save the model.
        """
        res = {}
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = {
                'cost': 0.0,
                'percentage': 0.0,
                'net_cost': 0.0,  # Equal to cost for now
                'new_net_cost': 0.0,  # Equal to new cost for now
            }
            res[line.id]['new_net_cost'] = line.new_cost
            domain = [('change_id', '!=', line.change_id.id),
                      ('change_id.partner_id', '=',
                       line.change_id.partner_id.id),
                      ('product_id', '=', line.product_id.id),
                      ('change_id.state', '=', 'updated')]
             # Search last lines for a different parent to get 'cost' field
            ch_lines = self.search(cr, uid, domain, context=context,
                                   limit=1, order='id desc')
            if ch_lines:
                last_line = self.browse(cr, uid, ch_lines[0], context=context)
                res[line.id]['cost'] = last_line.new_cost
                num = float(line.new_cost)
                den = float(res[line.id]['cost'])
                operation = ((num / den) - 1) * 100
                digitsp = dp.get_precision('Product Price')(cr)[1]
                res[line.id]['percentage'] = round(operation, digitsp)
                res[line.id]['net_cost'] = res[line.id]['cost']
        return res

    _columns = {
        'change_id': fields.many2one('change.supplier.cost',
                                     'Change supplier cost',
                                     ondelete='cascade'),
        'product_id': fields.many2one('product.product',
                                      'Product', required=True,
                                      domain=[('product_class',
                                               'in',
                                              ['dry', 'frozen', 'chilled'])]),
        'sup_code': fields.char('Supplier code', size=128),
        'cost': fields.function(_get_fields, method=True, type="float",
                                multi="get", string='Current cost',
                                digits_compute=
                                dp.get_precision('Product Cost'),
                                readonly=True),
        'new_cost': fields.float('New cost', required=True,
                                 digits_compute=
                                 dp.get_precision('Product Cost')),
        'percentage': fields.function(_get_fields, method=True, type="float",
                                      multi="get", string='Percentage',
                                      digits_compute=
                                      dp.get_precision('Product Price'),
                                      readonly=True),
        'net_cost': fields.function(_get_fields, method=True, type="float",
                                    multi="get",
                                    string='Net cost',
                                    digits_compute=
                                    dp.get_precision('Product Cost'),
                                    readonly=True),
        'new_net_cost': fields.function(_get_fields, method=True, type="float",
                                        multi="get", string='New Net cost',
                                        digits_compute=
                                        dp.get_precision('Product Cost'),
                                        readonly=True),
        'date': fields.date('Date', required=True),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, partner_id,
                            context=None):
        """
        Function that fills the Current cost, Net costs, corresponding each
        time we change the product.
        """
        if context is None:
            context = {}
        res = {'value': {'cost': 0.0, 'new_net_cost': 0.0, 'cmp_actual': 0.0}}
        if product_id:
            if ids:  # Search last line for a diferent parent model
                cur_line = self.browse(cr, uid, ids[0], context=context)
                chmodel = cur_line.change_id
                domain = [('change_id', '!=', chmodel.id),
                          ('change_id.partner_id', '=', chmodel.partner_id.id),
                          ('product_id', '=', product_id),
                          ('change_id.state', '=', 'updated')]
            else:
                domain = [('change_id.partner_id', '=', partner_id or False),
                          ('product_id', '=', product_id),
                          ('change_id.state', '=', 'updated')]
            ch_lines = self.search(cr, uid, domain, context=context,
                                   limit=1, order='id desc')
            if ch_lines:
                last_line = self.browse(cr, uid, ch_lines[0], context=context)
                res['value']['cost'] = last_line.new_cost
                res['value']['net_cost'] = res['value']['cost']
        return res

    def onchange_new_cost(self, cr, uid, ids, new_cost, cost, context=None):
        """
        Function that fills the percentage and new net cost fields
        corresponding each time we change the new cost.
        """
        if context is None:
            context = {}
        res = {'value': {'percentage': 0.0, 'new_net_cost': 0.0}}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        if new_cost:
            if cost:
                operation = (float(new_cost) / float(cost) - 1) * 100.0
                res['value']['percentage'] = round(operation, digitsp)
            res['value']['new_net_cost'] = new_cost
        return res

# ****************************************************************************
# **************************CHANGE PRODUCT PVP********************************
# ****************************************************************************


class change_product_pvp(osv.Model):
    """
    Change products pvp for no fresh products.
    It will we authomatic created when product cmc changes. and cmc changes
    with each product standar_price change.
    """
    _name = 'change.product.pvp'
    _rec_name = 'product_id'
    _order = 'date_cmc desc'
    _columns = {
        'product_id': fields.many2one('product.product', 'Product',
                                      readonly=True, required=True,
                                      domain=[('product_class',
                                               'in',
                                             ['dry', 'frozen', 'chilled'])]),
        'date_cmc': fields.datetime('Updated Date', readonly=True),  # required
        'cmc': fields.float('CMC', required=True,
                            digits_compute=
                            dp.get_precision('Product Price'),  # p cost?
                            readonly=True),
        'cmp': fields.float('CMP', required=True,  # p cost?
                            digits_compute=
                            dp.get_precision('Product Price'),
                            readonly=True),
        'sec_margin': fields.float('Security Margin', required=True,
                                   digits_compute=
                                   dp.get_precision('Product Price'),
                                   readonly=True),
        'real_stock': fields.float('Real Stock',
                                   digits_compute=
                                   dp.get_precision('Product Unit of Measure'),
                                   readonly=True),
        'virt_stock': fields.float('Virtual Stock',
                                   digits_compute=
                                   dp.get_precision('Product Unit of Measure'),
                                   readonly=True),
        'pricelist_ids': fields.one2many('pricelist.pvp.line',
                                         'change_id',
                                         'Pricelists & PVP'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('updated', 'Updated')], 'Status',
                                  required=True, readonly=True),
    }
    _defaults = {
        'state': 'draft'
    }

    def update_pricelists_pvp(self, cr, uid, ids, context=None):
        """
        Update model state to updated to be considerated when we search
        into this model.
        """
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'updated'}, context=context)
        return

    def cancel_pricelists_pvp(self, cr, uid, ids, context=None):
        """
        Update model state to draft to not be considerated when we search
        into this model.
        """
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        return


class pricelist_pvp_line(osv.Model):
    """
    This model are lines of change_variable_pricelist model.
    It defines the new prices for each pricelist.
    """
    _name = 'pricelist.pvp.line'
    _rec_name = 'pricelist_id'

    def _get_fields(self, cr, uid, ids, field_name, args, context=None):
        """
        Calculates margin and minimum margin.
        we must satisface that NEW_PVP * (1-(MARGIN/100)) = CMC
        """
        res = {}
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = {
                'margin': 0.0,
                'min_margin': 0.0,
            }
            digitsp = dp.get_precision('Product Price')(cr)[1]
            new_pvp = line.pvp
            cmc = line.change_id.cmc
            operation = (1 - float(cmc) / float(new_pvp)) * 100.0
            res[line.id]['margin'] = round(operation, digitsp)
            min_pvp = line.min_price
            operation = (1 - float(cmc) / float(min_pvp)) * 100.0
            res[line.id]['min_margin'] = round(operation, digitsp)
        return res

    _columns = {
        'change_id': fields.many2one('change.product.pvp',
                                     'Change product pvp',
                                     ondelete='cascade'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
                                        required=True,
                                        domain=[('type', '=', 'sale')]),
        'pvp': fields.float('Price (PVP)', required=True,
                            digits_compute=
                            dp.get_precision('Product Price')),
        'margin': fields.float('Margin',
                               digits_compute=
                               dp.get_precision('Product Price')),
        'min_price': fields.float('Minimum Price',
                                  digits_compute=
                                  dp.get_precision('Product Price')),
        'min_margin': fields.float('Minimum Margin',
                                   digits_compute=
                                   dp.get_precision('Product Price')),
        'date_start': fields.date('Start Date', required=True),
        'date_end': fields.date('End Date', required=True),
    }

    def _check_dates(self, cr, uid, ids, context=None):
        """
        Checks 'date start' and 'date end' to avoid overlaped dates for the
        same pricelist in the same change_product_pvp model
        """
        for chg_line in self.browse(cr, uid, ids, context=context):
            domain = [
                ('id', 'not in', ids),
                ('change_id', '=', chg_line.change_id.id),
                ('pricelist_id', '=', chg_line.pricelist_id.id),
                '&', '|',
                ('date_start', '<=', chg_line.date_start),
                ('date_end', '>=', chg_line.date_start),
                '&',
                ('date_start', '<=', chg_line.date_end),
                ('date_end', '>=', chg_line.date_end),
            ]
            search_ids = self.search(cr, uid, domain, context=context)
            if search_ids:  # Means overlaped dates
                return False
        return True

    _constraints = [
        (_check_dates,
         'You cannot have 2 change product pvp lines whith overlaped dates! \
         for the same product',
         ['date_start', 'date_end'])
    ]

    def onchange_pvp(self, cr, uid, ids, new_pvp, cmc, context=None):
        """
        Change margin. We must satisface that NEW_PVP * (1-(MARGIN/100)) = CMC
        """
        if context is None:
            context = {}
        res = {'value': {}}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        if new_pvp and cmc:
            operation = (1 - float(cmc) / float(new_pvp)) * 100.0
            res['value']['margin'] = round(operation, digitsp)
            # import ipdb; ipdb.set_trace()
        return res

    def onchange_min_price(self, cr, uid, ids, min_price, cmc, context=None):
        """
        Change min_margin. We must satisface that
        MIN_PRICE * (1-(MIN_MARGIN/100)) = CMC
        """
        if context is None:
            context = {}
        res = {'value': {}}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        if min_price and cmc:
            operation = (1 - float(cmc) / float(min_price)) * 100.0
            res['value']['min_margin'] = round(operation, digitsp)
            # import ipdb; ipdb.set_trace()
        return res

    def onchange_margin(self, cr, uid, ids, margin, cmc, context=None):
        """
        Change PVP. We must satisface that PVP * (1-(MARGIN/100)) = CMC
        """
        if context is None:
            context = {}
        res = {'value': {}}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        if margin and cmc:
            operation = float(cmc) / (1 - (float(margin) / 100.0))
            res['value']['pvp'] = round(operation, digitsp)
            # import ipdb; ipdb.set_trace()
        return res

    def onchange_min_margin(self, cr, uid, ids, min_margin, cmc, context=None):
        """
        Change min_price. We must satisface that
        MIN_PRICE * (1-(MIN_MARGIN/100)) = CMC
        """
        if context is None:
            context = {}
        res = {'value': {}}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        if min_margin and cmc:
            operation = float(cmc) / (1 - (float(min_margin) / 100.0))
            res['value']['min_price'] = round(operation, digitsp)
            # import ipdb; ipdb.set_trace()
        return res

# ****************************************************************************
# **************************SPECIFIC CUSTOMER PVP*****************************
# ****************************************************************************


class specific_customer_pvp(osv.Model):
    """
    Specific product PVP's for a custumer.
    If state is Updated when we do a sale order and we sale a product defined
    here for a current date betwen product line range of dates. We use the
    line price instead of pricelist price
    """
    _name = 'specific.customer.pvp'
    _rec_name = 'partner_id'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer',
                                      required=True,
                                      domain=[('customer', '=', True)]),
        'product_ids': fields.one2many('specific.pvp.line',
                                       'specific_id',
                                       'Products & PVP'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('updated', 'Updated')], 'Status',
                                  required=True, readonly=True),
    }
    _defaults = {
        'state': 'draft'
    }

    def approve_specific_pvp(self, cr, uid, ids, context=None):
        """
        Update model state to updated to be considerated when we search
        into this model.
        """
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'updated'}, context=context)
        return

    def cancel_specific_pvp(self, cr, uid, ids, context=None):
        """
        Update model state to updated to be considerated when we search
        into this model.
        """
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        return


class specific_pvp_line(osv.Model):
    """
    Lines of specific_customer_pvp model.
    It defines for a product and a date range a specific price when we sale
    the product.
    For no fresh products
    """
    _name = 'specific.pvp.line'
    _rec_name = 'product_id'

    def _get_fields(self, cr, uid, ids, field_name, args, context=None):
        """
        Function to get cmc and pvp looking for change_product_pvp lines.
        """
        res = {}
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = {
                'cmc': 0.0,
                'pvp': 0.0,
            }
            pvp_line = self.pool.get("pricelist.pvp.line")
            t_partner = self.pool.get("res.partner")
            partner = t_partner.browse(cr, uid, line.specific_id.partner_id.id,
                                       context)

            if not partner or not line.product_id:
                continue
            pricelist_id = partner.property_product_pricelist.id
            domain = [('change_id.product_id', '=', line.product_id.id),
                      ('change_id.state', '=', 'updated'),
                      ('pricelist_id', '=', pricelist_id),
                      ('date_start', '<=', time.strftime('%Y-%m-%d')),
                      ('date_end', '>=', time.strftime('%Y-%m-%d'))]
            line_ids = pvp_line.search(cr, uid, domain, limit=1,
                                       order='id desc')
            if not line_ids:
                continue
            ch_line = pvp_line.browse(cr, uid, line_ids[0])
            res[line.id]['cmc'] = ch_line.change_id.cmc
            res[line.id]['pvp'] = ch_line.pvp
        return res

    _columns = {
        'specific_id': fields.many2one('specific.customer.pvp',
                                       'Specific model',
                                       ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product',
                                      required=True,
                                      domain=[('product_class',
                                               'in',
                                               ['dry', 'frozen', 'chilled'])]),
        'cmc': fields.function(_get_fields, method=True, type="float",
                               multi="get", string='CMC',
                               digits_compute=
                               dp.get_precision('Product Cost'),
                               readonly=True),
        'pvp': fields.function(_get_fields, method=True, type="float",
                               multi="get", string='PVP',
                               digits_compute=
                               dp.get_precision('Product Price'),
                               readonly=True),
        'margin': fields.float('Margin',
                               digits_compute=
                               dp.get_precision('Product Price')),
        'specific_pvp': fields.float('Specific PVP',
                                     digits_compute=
                                     dp.get_precision('Product Price'),
                                     required=True),
        '2net_margin': fields.float('Net Net Margin', readonly=True,
                                    digits_compute=
                                    dp.get_precision('Product Price')),
        'date_start': fields.date('Start Date', required=True),
        'date_end': fields.date('End Date', required=True),
        'note': fields.char('Note', size=256),
        # To avoid calls between onchanges
        'do_onchange': fields.boolean('Do onchange')
    }

    def _check_dates(self, cr, uid, ids, context=None):
        """
        Checks 'date start' and 'date end' to avoid overlaped dates for the
        same product in the same specific_customer_pvp model.
        """
        for spec_line in self.browse(cr, uid, ids, context=context):
            domain = [
                ('id', 'not in', ids),
                ('specific_id', '=', spec_line.specific_id.id),
                ('product_id', '=', spec_line.product_id.id),
                '&', '|',
                ('date_start', '<=', spec_line.date_start),
                ('date_end', '>=', spec_line.date_start),
                '&',
                ('date_start', '<=', spec_line.date_end),
                ('date_end', '>=', spec_line.date_end),
            ]
            search_ids = self.search(cr, uid, domain, context=context)
            if search_ids:  # Means overlaped dates.
                return False
        return True

    _constraints = [
        (_check_dates,
         'You cannot have 2 specific product pvp whith overlaped dates!',
         ['date_start', 'date_end'])
    ]

    def onchange_product_id(self, cr, uid, ids, product_id, partner_id,
                            context=None):
        """
        Change CMC and PVP. Searching into change_product_pvp lines like if
        you do a sale order with no fresh pricelist.
        """
        if context is None:
            context = {}
        res = {'value': {}}
        if not partner_id:
            msg = _('Please select a partner for apply specific prices')
            res['warning'] = {'title': _('Warning!'),
                              'message': msg}
        if product_id and partner_id:
            pvp_line = self.pool.get("pricelist.pvp.line")
            t_partner = self.pool.get("res.partner")
            partner = t_partner.browse(cr, uid, partner_id, context)
            pricelist_id = partner.property_product_pricelist.id
            domain = [('change_id.product_id', '=', product_id),
                      ('change_id.state', '=', 'updated'),
                      ('pricelist_id', '=', pricelist_id),
                      ('date_start', '<=', time.strftime('%Y-%m-%d')),
                      ('date_end', '>=', time.strftime('%Y-%m-%d'))]
            line_ids = pvp_line.search(cr, uid, domain, limit=1,
                                       order='id desc')
            if not line_ids:
                res['warning'] = {'title': _('Warning!'),
                                  'message': _('There is no change \
                                                product pvp for \
                                                this product.')}
                return res
            line = pvp_line.browse(cr, uid, line_ids[0])
            res['value']['cmc'] = line.change_id.cmc
            res['value']['pvp'] = line.pvp
        return res

    def onchange_specific_pvp(self, cr, uid, ids, new_pvp, cmc, do_onchange,
                              context=None):
        """
        Change margin. We must satisface that NEW_PVP * (1-(MARGIN/100)) = CMC
        do_onchange to avoid rounding problems becaous of when we change margin
        it will we execute margin on change. It is not correct.
        """
        if context is None:
            context = {}
        res = {'value': {}}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        if new_pvp and do_onchange:
            operation = (1 - float(cmc) / float(new_pvp)) * 100.0
            res['value']['margin'] = round(operation, digitsp)
            res['value']['do_onchange'] = False
        if not do_onchange:
            res['value']['do_onchange'] = True
            # import ipdb; ipdb.set_trace()
        return res

    def onchange_margin(self, cr, uid, ids, margin, cmc, do_onchange,
                        context=None):
        """
        Change specific_pvp. We must satisface:
        NEW_PVP * (1-(MARGIN/100)) = CMC
        do_onchange to avoid rounding problems becaous of when we change margin
        it will we execute margin on change. It is not correct.
        """
        if context is None:
            context = {}
        res = {'value': {}}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        if margin == 100.0:
            res['warning'] = {'title': _('Warning!'),
                              'message': _('Margin must be less than 100 \
                                           please change it')}
            res['value']['margin'] = 99.99
            operation = float(cmc) / (1 - (float(99.99) / 100.0))
            res['value']['specific_pvp'] = round(operation, digitsp)
            res['value']['do_onchange'] = False
        elif do_onchange:
            operation = float(cmc) / (1 - (float(margin) / 100.0))
            res['value']['specific_pvp'] = round(operation, digitsp)
            res['value']['do_onchange'] = False
        elif not do_onchange:
            res['value']['do_onchange'] = True
        return res
