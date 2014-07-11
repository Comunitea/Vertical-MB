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
# from openerp.tools.translate import _


import openerp.addons.decimal_precision as dp


class wzd_update_cmc(osv.osv_memory):
    _name = "wzd.update.cmc"
    _columns = {
        'new_cmc': fields.float('CMC',
                                digits_compute=
                                dp.get_precision('Product Cost'),
                                groups="base.group_user",
                                required=True),
        'new_sec_margin': fields.float('Security Margin', required=True,
                                       digits_compute=
                                       dp.get_precision('Product Price')),
        'do_onchange': fields.boolean('Do onchange')
    }
    _defaults = {
        'do_onchange': True
    }

    # def default_get(self, cr, uid, fields, context=None):
    #     res = super(wzd_update_cmc, self).default_get(cr, uid, fields,
    #                                                   context=context)
    #     t_product = self.pool.get("product.product")
    #     # si llamas al wizard haciendo un crear nuevo tiene id el active_id??
    #     if context.get('active_id', False):
    #         product = t_product.browse(cr, uid, context['active_id'],
    #                                    context=context)
    #         res.update({'new_cmc': product.cmc or 0.0,
    #                     'new_sec_margin': product.sec_margin or 0.0})

    #     return res

    def onchange_new_sec_margin(self, cr, uid, ids, sec_margin, do_onchange,
                                context=None):
        """
        Function that fills the New CMC price corresponding each time we change
        the security margin.
        """
        if context is None:
            context = {}
        t_product = self.pool.get("product.product")
        res = {'value': {}}
        # import ipdb; ipdb.set_trace()
        if context.get('active_id', False) and do_onchange:
            # import ipdb; ipdb.set_trace()
            prod = t_product.browse(cr, uid, context['active_id'], context)
            prod_cmp = prod.standard_price
            res = {'value': {'new_cmc': 0.0}}
            digitsc = dp.get_precision('Product Cost')(cr)[1]
            operation = prod_cmp * (1 + sec_margin / 100.0)
            res['value']['new_cmc'] = round(operation, digitsc)
            res['value']['do_onchange'] = False
        if not do_onchange:
            res['value']['do_onchange'] = True
        return res

    def onchange_new_cmc(self, cr, uid, ids, new_cmc, do_onchange,
                         context=None):
        """
        Function that fills the security margin percentage corresponding each
        time we change the New CMC.
        """
        if context is None:
            context = {}
        t_product = self.pool.get("product.product")
        res = {'value': {}}
        # import ipdb; ipdb.set_trace()
        if context.get('active_id', False) and do_onchange:
            # import ipdb; ipdb.set_trace()
            prod = t_product.browse(cr, uid, context['active_id'], context)
            prod_cmp = prod.standard_price
            digitsp = dp.get_precision('Product Price')(cr)[1]
            if new_cmc and prod_cmp:
                operation = (float(new_cmc) / float(prod_cmp) - 1) * 100.0
                res['value']['new_sec_margin'] = round(operation, digitsp)
            res['value']['do_onchange'] = False
        if not do_onchange:
            res['value']['do_onchange'] = True
        return res

    def update_cmc(self, cr, uid, ids, context=None):
        """
        Write new cmc in product and create a new change_productr_pvp model
        """
        if context is None:
            context = {}
        t_product = self.pool.get("product.product")
        wzd_obj = self.browse(cr, uid, ids[0], context)
        if context.get('active_id', False):
            vals = {'cmc': wzd_obj.new_cmc,
                    'sec_margin': wzd_obj.new_sec_margin
                    }
            prod_obj = t_product.browse(cr, uid, context['active_id'])
            prod_obj.write(vals)
            t_product._create_change_pvp(cr, uid, [context['active_id']],
                                         wzd_obj.new_cmc,
                                         prod_obj.standard_price,
                                         context=context)
        return {'type': 'ir.actions.act_window_close'}
