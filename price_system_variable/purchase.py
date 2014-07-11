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
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import time
import openerp.addons.decimal_precision as dp


class purchase_order(osv.Model):
    _inherit = "purchase.order"

    def _search_variable_pricelist(self, cr, uid, ids, product, context=None):
        """
        Search variable_pricelist first by product, Second by category
        and finally by parents category in order (closest parents first)
        """
        if context is None:
            context = {}
        t_variable = self.pool.get("variable.pricelist")
        t_category = self.pool.get("product.category")
        # First search by product
        domain = [('product_id', '=', product.id)]
        vpl_ids = t_variable.search(cr, uid, domain,
                                    context=context)
        if not vpl_ids:
            # Second search by category
            domain = [('categ_id', '=', product.categ_id.id)]
            vpl_ids = t_variable.search(cr, uid, domain,
                                        context=context)
            if not vpl_ids:
                # Finally search parent categorys by closest parent first
                domain = [('parent_left', '<', product.categ_id.parent_left),
                          ('parent_right', '>', product.categ_id.parent_right)]
                cat_ids = t_category.search(cr, uid, domain, context=context,
                                            order='parent_left desc')
                for cat_id in cat_ids:
                    domain = [('categ_id', '=', cat_id)]
                    list_ids = t_variable.search(cr, uid, domain,
                                                 context=context)
                    if list_ids:
                        vpl_ids.append(list_ids[0])
                        return vpl_ids
        return vpl_ids

    def _calc_prices(self, cr, uid, ids, line, change_id, margin_obj,
                     context=None):
        """
        Calculate prices of change_variable_pricelist lines.
        """
        if context is None:
            context = {}
        res = {'previous_cost': 0.0, 'current_cost': 0.0, 'real_margin': 0.0,
               'previous_pvp': 0.0, 'current_pvp': 0.0}
        t_chg_line = self.pool.get("variable.change.line")
        digitsp = dp.get_precision('Product Price')(cr)[1]
        digitsc = dp.get_precision('Product Cost')(cr)[1]
        # PREVIOUS COST: CMP last purchase (last purchase = current purchase)
        # we ponderate. Most times not necesary for fresh products
        real_stock = line.product_id.qty_available
        price = line.product_id.standard_price
        num = (real_stock * price) + (line.product_qty * line.price_unit)
        den = real_stock + line.product_qty
        res['previous_cost'] = round(num / den, digitsc)
        margin = margin_obj.margin
        sec_margin = margin_obj.range_id.security_margin
        # CURRENT COST: Apply margin of margin_table to previous_cost
        res['current_cost'] = res['previous_cost'] * (1 + (sec_margin / 100.0))
        res['current_cost'] = round(res['current_cost'], digitsc)
        # REAL MARGIN: Margin Applied (It's provited by margin table)
        res['real_margin'] = margin
        # PREVIOS PVP: Last variable_change_pricelist model for current product
        domain = [('change_id', '!=', change_id),
                  ('change_id.product_id', '=', line.product_id.id),
                  ('pricelist_id', '=', margin_obj.pricelist_id.id),
                  ('change_id.state', '=', 'updated')]
        chg_line_ids = t_chg_line.search(cr, uid, domain, context=context,
                                         limit=1, order='id desc')
        for chlin in t_chg_line.browse(cr, uid, chg_line_ids, context=context):
            res['previous_pvp'] = chlin.current_pvp
        # CURRENT PVP: pvp mus satisface PVP - REAL_MARGIN = CURRENT_COST so..
        # PVP = CURRENT_COST / (1 - (REAL_MARGIN/100)
        res['current_pvp'] = res['current_cost'] / (1 - (margin / 100.0))
        res['current_pvp'] = round(res['current_pvp'], digitsp)
        return res

    def _create_change_pricelist(self, cr, uid, ids, vpl_id, line,
                                 context=None):
        """
        Creates model change_variable_pricelist when a purchase order is
        confirmed looking into his margin table.
        """
        if context is None:
            context = {}
        t_range = self.pool.get("pricelist.range")
        t_margin = self.pool.get("pricelist.margin")
        t_change = self.pool.get("change.variable.pricelist")
        t_chg_line = self.pool.get("variable.change.line")
        # Search the right row from margin table or raises an error
        domain = [('var_pricelist_id', '=', vpl_id),
                  ('from_cost', '<=', line.price_unit),
                  ('to_cost', '>=', line.price_unit)]
        range_id = t_range.search(cr, uid, domain, context=context)
        if not range_id:
            msg = 'No valid range found in margin table for product: {} \
                   and cost price: {}'.format(line.product_id.name,
                                              line.price_unit)
            raise osv.except_osv(_('Error'), _(msg))
        range_id = range_id[0]
        domain = [('range_id', '=', range_id)]
        margin_ids = t_margin.search(cr, uid, domain, context=context)
        if not margin_ids:
            msg = _('No columns found in margin table for current price range')
            raise osv.except_osv(_('Error'), msg)
        # Create the model change_variable_pricelist
        vals = {'date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'product_id': line.product_id.id,
                'purchase_id': line.order_id.id,
                'name': 'Actualizar {}'.format(time.strftime("%Y-%m-%d \
                                                             %H:%M:%S"))
                }
        change_id = t_change.create(cr, uid, vals, context=context)
        for margin_obj in t_margin.browse(cr, uid, margin_ids,
                                          context=context):
            # Calc prices and margin
            prices = self._calc_prices(cr, uid, ids, line, change_id,
                                       margin_obj, context=context)
            note = 'El coste anterior y el actual difieren en mas de un 10%'
            label = False
            diff = prices['current_cost'] - prices['previous_cost']
            if (diff / prices['previous_cost']) > 0.1:
                label = True
            vals = {'change_id': change_id,
                    'pricelist_id': margin_obj.pricelist_id.id,
                    'previous_cost': prices['previous_cost'],
                    'current_cost': prices['current_cost'],
                    'real_margin': prices['real_margin'],  # ????
                    'previous_pvp': prices['previous_pvp'],
                    'current_pvp': prices['current_pvp']}
            t_chg_line.create(cr, uid, vals, context=context)
        t_change.write(cr, uid, change_id, {'note': note, 'label': label},
                       context=context)
        return

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        """
        If a purchase order line is marked as update_pricelist when it is
        confirmed, we generate the model chande_variable_pricelist for
        fresh products,
        """
        if context is None:
            context = {}
        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids,
                                                            context=context)
        for po in self.browse(cr, uid, ids, context=context):
            for line in po.order_line:
                if line.update_pricelist and \
                   line.product_id.product_class == 'fresh':
                    # Get a list of variable_pricelist ids for the product.
                    # order by sequence
                    vpl_ids = self._search_variable_pricelist(cr, uid, ids,
                                                              line.product_id,
                                                              context=context)
                    # If not variable pricelist for product raises an error.
                    if not vpl_ids:
                        msg = u'No category or product in variable pricelist \
                                compatible with product:{}'
                        msg.format(line.product_id.name)
                        raise osv.except_osv(_('Error'), _(msg))
                    # Use the firt variable_pricelist (priority low sequence)
                    # in order to generate the change_variable_pricelist model
                    self._create_change_pricelist(cr, uid, ids, vpl_ids[0],
                                                  line,
                                                  context=context)

        return res

    def change_pricelist_open(self, cr, uid, ids, context=None):
        """Open change_variable_pricelist model related to purchases"""
        if context is None:
            context = {}
        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference(cr, uid, 'price_system_variable',
                                            'action_change_variable_pricelist')
        action = self.pool.get(res[0]).read(cr, uid, res[1],
                                            context=context)

        domain = str([('purchase_id', 'in', ids)])
        action['domain'] = domain
        return action

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Overwrited in order to not cancel a purchase order if it has
        Change variable pricelist models related.
        """
        if context is None:
            context = {}
        t_change = self.pool.get("change.variable.pricelist")
        for purchase in self.browse(cr, uid, ids, context=context):
            domain = [('purchase_id', '=', purchase.id),
                      ('state', '=', 'updated')]
            chg_ids = t_change.search(cr, uid, domain, context=context)
            if chg_ids:
                raise osv.except_osv(
                    _('Unable to cancel this purchase order.'),
                    _('You must first cancel all Variable change pricelist \
                        related'))
            else:
                domain = [('purchase_id', '=', purchase.id),
                          ('state', '=', 'draft')]
                chg_ids = t_change.search(cr, uid, domain, context=context)
                t_change.unlink(cr, uid, chg_ids, context=context)

        return super(purchase_order, self).action_cancel(cr, uid, ids,
                                                         context=context)


class purchase_order_line(osv.Model):
    _inherit = 'purchase.order.line'
    _columns = {
        'update_pricelist': fields.boolean('Update pricelist'),
        'price_unit': fields.float('Unit Price', required=True,
                                   digits_compute=
                                   dp.get_precision('Product Cost')),
    }

    def onchange_price_unit(self, cr, uid, ids, product_id, price_unit,
                            context=None):
        """
        Onchange handler of product_unit. If price_unit is different than
        product standard_price we mark line a update_pricelist
        """
        res = {'value': {'price_unit': price_unit or 0.0,
                         'update_pricelist': False}}
        if context is None:
            context = {}
        product = self.pool.get("product.product").browse(cr, uid, product_id,
                                                          context=context)
        if (product.product_class == 'fresh') and \
           (product.standard_price != price_unit):
            res['value'].update({'update_pricelist': True})
        return res

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty,
                            uom_id, partner_id, date_order=False,
                            fiscal_position_id=False, date_planned=False,
                            name=False, price_unit=False, state='draft',
                            context=None):
        """
        Overwrite onchange_product_id in order to get the correct price when
        purchase pricelist rule is based on change_supplier_costs (base = -4)
        or raise a warning if anyone was found.
        """

        sup = super(purchase_order_line, self)
        res = sup.onchange_product_id(cr, uid, ids, pricelist_id, product_id,
                                      qty, uom_id, partner_id,
                                      date_order=date_order,
                                      fiscal_position_id=
                                      fiscal_position_id,
                                      date_planned=date_planned,
                                      name=name,
                                      price_unit=price_unit,
                                      state=state,
                                      context=context)
        # All this COPY-PASTED in order to found the pricelist rule type
        # (field base) apply to current purchase
        if not product_id:
            return res
        product_product = self.pool.get('product.product')
        res_partner = self.pool.get('res.partner')
        t_plist = self.pool.get('product.pricelist')
        t_product = self.pool.get('product.product')
        t_item = self.pool.get('product.pricelist.item')
        context_partner = context.copy()
        if pricelist_id:
            if partner_id:
                lang = res_partner.browse(cr, uid, partner_id).lang
                context_partner.update({'lang': lang,
                                        'partner_id': partner_id})
            product = product_product.browse(cr, uid, product_id,
                                             context=context_partner)
            product_uom_po_id = product.uom_po_id.id
            if not uom_id:
                uom_id = product_uom_po_id
            if not date_order:
                date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            context2 = {
                'uom': uom_id,
                'date': date_order
            }
            # price_get_multi return a dict with the property pricelit rule
            # for the product
            prod_obj = t_product.browse(cr, uid, product_id, context)
            res_multi = t_plist.price_get_multi(cr, uid,
                                                pricelist_ids=[pricelist_id],
                                                products_by_qty_by_partner=
                                                [(prod_obj, qty or 1.0,
                                                 partner_id)],
                                                context=context2)
            if res_multi[product_id] == dict:
                item_id = res_multi[product_id].get('item_id', False)
            else:
                item_id = False
            # END OF COPY PASTE

            # res['value'].update({'update_pricelist': False}) ??????????????
            if item_id:
                item = t_item.browse(cr, uid, item_id)
                if item.base == -4:
                    price_dic = t_plist.price_get(cr, uid,
                                                  [pricelist_id],
                                                  product_id,
                                                  qty or 1.0,
                                                  partner_id or False,
                                                  {'uom': uom_id,
                                                   'date': date_order})
                    price_code = price_dic[pricelist_id]
                    price = price_code[0]
                    if price == "warn":
                        price = 0.0
                        res['warning'] = {'title': _('Warning!'),
                                          'message': _('There is no supplier \
                                                       pricelist rule for \
                                                       this product.')}
                    if price_code[1]:
                        res['value']['name'] = '[%s] %s' % (price_code[1],
                                                            product.name)
                    res['value']['price_unit'] = price
        return res
