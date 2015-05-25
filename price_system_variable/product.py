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
import time


class product_template(osv.Model):
    """Overwrite in order to add custom digit precision Product cost for cost
       prices with four decimal"""
    _inherit = "product.template"
    # Add 4 decimals in standard_price (defined in data/price_data.xml)
    _columns = {
        'standard_price': fields.property(type='float',
                                          digits_compute=dp.get_precision
                                          ('Product Cost'),
                                          help="Cost price of the product \
                                          template used for standard stock \
                                          valuation in accounting and used as \
                                          a base price on purchase orders.",
                                          groups="base.group_user",
                                          string="Cost Price"),
        'cmc': fields.float('CMC',
                            digits_compute=dp.get_precision('Product Cost'),
                            readonly=True,),
        'sec_margin': fields.float('Security Margin', readonly=True,
                                   digits_compute=dp.get_precision
                                   ('Product Price')),
    }

    def _create_change_pvp(self, cr, uid, ids, new_cmc, new_sp, context=None):
        """
        Method to create a change product pvp model.
        """
        if context is None:
            context = {}
        change_pvp = self.pool.get("change.product.pvp")
        change_line = self.pool.get("pricelist.pvp.line")
        t_pricelist = self.pool.get("product.pricelist")
        digitsp = dp.get_precision('Product Price')(cr)[1]
        for product in self.browse(cr, uid, ids, context):
            vals = {'product_id': product.id,
                    'cmc': new_cmc or 0.0,
                    'date_cmc': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'cmp': new_sp or 0.0,
                    'sec_margin': product.sec_margin or 0.0,
                    'real_stock': product.qty_available or 0.0,
                    'virt_stock': product.virtual_available or 0.0,
                    'state': 'draft'
                    }
            # Search no applied models to delete it
            domain = [('state', '=', 'draft'),
                      ('product_id', '=', product.id),
                      ]
            no_apply_ids = change_pvp.search(cr, uid, domain, context=context)
            change_pvp.unlink(cr, uid, no_apply_ids)
            ch_id = change_pvp.create(cr, uid, vals, context=context)
            # Look for pricelist containing rules based on change pvp base = -5
            pric_ids = t_pricelist._get_pricelist_based_in_x(cr, uid, '-5')
            for p_id in pric_ids:
                pvp_line = self.pool.get("pricelist.pvp.line")
                domain = [('change_id.product_id', '=', product.id),
                          ('change_id.state', '=', 'updated'),
                          ('pricelist_id', '=', p_id)]
                # Search price and min price in the last updated change pvp
                # model.
                line_ids = pvp_line.search(cr, uid, domain, limit=1,
                                           order='id desc')
                pvp = min_pvp = margin = min_margin = 0.0
                date_start = date_end = time.strftime("%Y-%m-%d %H:%M:%S")
                if line_ids:  # If last model exist, set values to last model
                    line = pvp_line.browse(cr, uid, line_ids[0])
                    pvp = line.pvp
                    min_pvp = line.min_price
                    if pvp and new_cmc:
                        operation = (1 - float(new_cmc) / float(pvp)) * 100.0
                        margin = round(operation, digitsp)
                    if min_pvp and new_cmc:
                        operation = (1 - float(new_cmc) / float(min_pvp)) \
                            * 100.0
                        min_margin = round(operation, digitsp)
                    date_start = line.date_start
                    date_end = line.date_end
                vals = {'change_id': ch_id,
                        'pricelist_id': p_id,
                        'pvp': pvp,
                        'margin': margin,
                        'min_price': min_pvp,
                        'min_pvp': min_pvp,
                        'min_margin': min_margin,
                        'date_start': date_start,
                        'date_end': date_end}
                # create as lines as pricelist founded.
                change_line.create(cr, uid, vals, context)
        return

    def write(self, cr, uid, ids, vals, context=None):
        """
        Calculates all readonly cmc and security margin fields.
        Also recalculate cmc and generate a change_product_pvp when
        standard_price change.
        """
        if context is None:
            context = {}
        digitsp = dp.get_precision('Product Price')(cr)[1]
        for p in self.browse(cr, uid, ids, context):
            # if standard_price change update cmc and create change_product_pvp
            if vals.get('standard_price', False) and \
               vals['standard_price'] != p.standard_price:
                new_cmc = vals['standard_price'] * (1 + p.sec_margin / 100.0)
                new_cmc = round(new_cmc, digitsp)
                vals.update({'cmc': new_cmc})
                # Generate change pvp model
                self._create_change_pvp(cr, uid, ids, new_cmc,
                                        vals['standard_price'],
                                        context=context)
        return super(product_template, self).write(cr, uid, ids, vals, context)

    def _get_pvp_changes(self, cr, uid, ids, context=None):
        """
        Return ids of action_change_product_pvp model whitch product equal to
        current product.
        """
        change_pvp = self.pool.get("change.product.pvp")
        domain = [('product_id', '=', ids[0])]
        show_ids = change_pvp.search(cr, uid, domain, context=context)
        return show_ids

    def show_pvp_changes(self, cr, uid, ids, context=None):
        """
        Returns a view of change_product_pvp related to current product.
        """
        if context is None:
            context = {}
        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference(cr, uid, 'price_system_variable',
                                            'action_change_product_pvp')
        action = self.pool.get(res[0]).read(cr, uid, res[1],
                                            context=context)

        list_ids = self._get_pvp_changes(cr, uid, ids, context=context)
        domain = str([('id', 'in', list_ids)])
        action['domain'] = domain

        return action


class pricelist_partnerinfo(osv.Model):

    _inherit = 'pricelist.partnerinfo'
    _order = 'from_date asc'

    _columns = {
        'from_date': fields.date('Init date'),
        'to_date': fields.date('End date'),
    }

