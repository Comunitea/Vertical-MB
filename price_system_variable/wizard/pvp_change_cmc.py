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


class pvp_change_cmc(osv.osv_memory):
    _name = "pvp.change.cmc"
    _columns = {
        'cmc': fields.float('CMC',
                            digits_compute=
                            dp.get_precision('Product Cost'),
                            groups="base.group_user",
                            required=True),
        'sec_margin': fields.float('Security Margin', required=True,
                                   digits_compute=
                                   dp.get_precision('Product Price')),
        'do_onchange': fields.boolean('Do onchange')  # Avoid rounding errors
    }
    _defaults = {
        'do_onchange': True
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(pvp_change_cmc, self).default_get(cr, uid, fields,
                                                      context=context)
        t_change = self.pool.get("change.product.pvp")
        # si llamas al wizard haciendo un crear nuevo tiene id el active_id??
        if context.get('active_id', False):
            change = t_change.browse(cr, uid, context['active_id'],
                                     context=context)
            res.update({'new_cmc': change.cmc or 0.0,
                        'new_sec_margin': change.sec_margin or 0.0})

        return res

    def update_cmc(self, cr, uid, ids, context=None):
        """
        Write new cmc in product and update marging related with cmc in the
        current model.
        """
        if context is None:
            context = {}
        # import ipdb
        # ipdb.set_trace()
        t_product = self.pool.get("product.product")
        t_change = self.pool.get("change.product.pvp")
        digitsp = dp.get_precision('Product Price')(cr)[1]
        wzd_obj = self.browse(cr, uid, ids[0], context)
        if context.get('active_id', False):
            vals = {'cmc': wzd_obj.cmc,
                    'sec_margin': wzd_obj.sec_margin
                    }
            change_obj = t_change.browse(cr, uid, context['active_id'])
            # Update product CMC and margin
            t_product.write(cr, uid, [change_obj.product_id.id], vals)
            # Update change model vals and related margins
            change_obj.write(vals)
            vals = {'margin': 0.0, 'min_margin': 0.0}
            for line in change_obj.pricelist_ids:
                if line.pvp == 0.0:
                    oper = 0.0
                else:
                    oper = (1 - float(wzd_obj.cmc) / float(line.pvp)) * 100.0
                vals['margin'] = round(oper, digitsp)
                if line.min_price == 0.0:
                    oper = 0.0
                else:
                    oper = (1 - float(wzd_obj.cmc) / float(line.min_price)) \
                        * 100.0
                vals['min_margin'] = round(oper, digitsp)
                line.write(vals)
        return {'type': 'ir.actions.act_window_close'}

    def onchange_sec_margin(self, cr, uid, ids, sec_margin, do_onchange,
                            context=None):
        """
        Function that fills the New CMC price corresponding each time we change
        the security margin.
        """
        if context is None:
            context = {}
        t_change = self.pool.get("change.product.pvp")
        res = {'value': {}}
        if context.get('active_id', False) and do_onchange:
            change = t_change.browse(cr, uid, context['active_id'], context)
            prod_cmp = change.product_id.standard_price
            digitsc = dp.get_precision('Product Cost')(cr)[1]
            operation = prod_cmp * (1 + sec_margin / 100.0)
            res['value']['cmc'] = round(operation, digitsc)
            res['value']['do_onchange'] = False
        if not do_onchange:
            res['value']['do_onchange'] = True
        return res

    def onchange_cmc(self, cr, uid, ids, new_cmc, do_onchange,
                     context=None):
        """
        Function that fills the security margin percentage corresponding each
        time we change the New CMC.
        """
        if context is None:
            context = {}
        t_change = self.pool.get("change.product.pvp")
        res = {'value': {}}
        if context.get('active_id', False) and do_onchange:
            change = t_change.browse(cr, uid, context['active_id'], context)
            prod_cmp = change.product_id.standard_price
            digitsp = dp.get_precision('Product Price')(cr)[1]
            if new_cmc and prod_cmp:
                operation = (float(new_cmc) / float(prod_cmp) - 1) * 100.0
                res['value']['sec_margin'] = round(operation, digitsp)
                res['value']['do_onchange'] = False
        if not do_onchange:
            res['value']['do_onchange'] = True
        return res
