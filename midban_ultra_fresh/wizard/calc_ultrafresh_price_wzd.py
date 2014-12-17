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
#############################################################################
# from openerp.osv import fields, osv
from openerp import models, fields, api
# from openerp.tools.translate import _


class calc_ultrafresh_price_wzd(models.TransientModel):
    """
    Wizard to recalculate the ultrafresh pvp in sales order.
    """
    _name = "calc.ultrafresh.price.wzd"

    date = fields.Date('Date', default=fields.Date.today())
    line_ids = fields.One2many('calc.price.line', 'wizard_id', 'Change lines')

    @api.onchange('date')
    def onchange_date(self):
        line_ids = []
        date_start = self.date + " 00:00:00"
        date_end = self.date + " 23:59:59"
        domain = [
            ('order_id.date_order', '>=', date_start),
            ('order_id.date_order', '<=', date_end),
            ('order_id.state', '=', 'approved'),
            ('order_id.ultrafresh_purchase', '=', True)
        ]
        line_objs = self.env['purchase.order.line'].search(domain)
        group = {}
        for line in line_objs:
            p_id = line.product_id.id
            if p_id not in group:
                group[p_id] = {
                    'num_purchases': 1,
                    'purchased_kg': line.purchased_kg,
                    'sum_prices': line.price_unit * line.purchased_kg,
                }
            else:
                group[p_id]['num_purchases'] = group[p_id]['num_purchases'] + 1
                group[p_id]['purchased_kg'] = group[p_id]['purchased_kg'] + \
                    line.purchased_kg
                group[p_id]['sum_prices'] = group[p_id]['sum_prices'] + \
                    (line.price_unit * line.purchased_kg)

        for key in group:
            prod_obj = self.env['product.product'].browse(key)
            margin = prod_obj.margin
            cost = prod_obj.standard_price
            final_pvp = cost / (1 - (margin / 100))
            vals = {
                'product_id': key,
                'num_purchases': group[key]['num_purchases'],
                'purchased_kg': group[key]['purchased_kg'],
                'avg_price_kg':
                group[key]['sum_prices'] / group[key]['num_purchases'],
                'margin': margin,
                'final_pvp': final_pvp,
                'calc_margin': margin,
            }
            line_ids.append(self.env['calc.price.line'].create(vals).id)
        self.line_ids = line_ids
        return

    def apply_changes(self):
        import ipdb; ipdb.set_trace()
        return


class calc_price_line(models.TransientModel):
    """ Lines to change ultrafresh prices"""
    _name = "calc.price.line"

    wizard_id = fields.Many2one('calc.ultrafresh.price.wzd', 'Wizard',
                                ondelete="cascade")
    product_id = fields.Many2one('product.product', 'Product',
                                 readonly=True)
    num_purchases = fields.Integer('Nº Purchases', readonly=True)
    purchased_kg = fields.Float('Purchased kg', readonly=True)
    avg_price_kg = fields.Float('Average Price kg ', readonly=True)
    margin = fields.Float('Margin ', readonly=True)
    final_pvp = fields.Float('Final pvp ')
    calc_margin = fields.Float('Calc Margin')

    @api.onchange('final_pvp')
    def onchange_final_pvp(self):
        cost = self.product_id.standard_price
        self.calc_margin = (1 - (cost / self.final_pvp)) * 100.0

    @api.onchange('calc_margin')
    def onchange_calc_margin(self):
        cost = self.product_id.standard_price
        self.final_pvp = (cost / (1 - (self.calc_margin / 100.0)))