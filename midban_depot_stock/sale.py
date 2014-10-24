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
from openerp.osv import osv, fields
from openerp.tools import float_compare
from openerp.tools.translate import _


class sale_order(osv.Model):
    _inherit = 'sale.order'

    _columns = {
        'route_id': fields.many2one('route', 'Transport Route',
                                    domain=[('state', '=', 'active')],
                                    readonly=True, states={'draft':
                                                           [('readonly',
                                                             False)],
                                                           'sent':
                                                           [('readonly',
                                                             False)]}),
    }

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        """
        When changing the partner the asociated route is filled, if any.
        """
        res = super(sale_order, self).onchange_partner_id(cr,
                                                          uid,
                                                          ids,
                                                          part=part,
                                                          context=context)
        partner_t = self.pool.get('res.partner')
        part = partner_t.browse(cr, uid, part, context=context)
        if not res['value'].get('route_id', []):
            if part.route_id:
                res['value']['route_id'] = part.route_id.id
        return res

    def _prepare_order_line_procurement(self, cr, uid, order, line,
                                        group_id=False, context=None):
        res = super(sale_order, self).\
            _prepare_order_line_procurement(cr, uid, order, line,
                                            group_id=group_id, context=context)
        res['route_id'] = order.route_id.id
        return res


class sale_order_line(osv.Model):
    _inherit = 'sale.order.line'

    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product,
                                  qty=0, uom=False, qty_uos=0, uos=False,
                                  name='', partner_id=False, lang=False,
                                  update_tax=True, date_order=False,
                                  packaging=False, fiscal_position=False,
                                  flag=False, warehouse_id=False,
                                  context=None):
        context = context or {}
        product_uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        warning = {}
        supe = super(sale_order_line, self)
        res = supe.product_id_change_with_wh(cr, uid, ids, pricelist, product,
                                             qty=qty, uom=False,
                                             qty_uos=qty_uos, uos=uos,
                                             name=name, partner_id=partner_id,
                                             lang=lang, update_tax=update_tax,
                                             date_order=date_order,
                                             packaging=packaging,
                                             fiscal_position=fiscal_position,
                                             flag=flag, context=context)
        import ipdb; ipdb.set_trace()
        # Compare stock agains virtual_stock_conservative
        prod_obj = product_obj.browse(cr, uid, product, context=context)
        warning_msgs = ''
        uom_record = False
        if uom:
            uom_record = product_uom_obj.browse(cr, uid, uom, context=context)
            if prod_obj.uom_id.category_id.id != uom_record.category_id.id:
                uom_record = False
        if not uom_record:
            uom_record = prod_obj.uom_id
        compare_qty = float_compare(prod_obj.virtual_stock_conservative, qty,
                                    precision_rounding=uom_record.rounding)
        if compare_qty == -1:
            warn_msg = _('You plan to sell %.2f %s but you only have %.2f %s \
                          available in conservative !\nThe real stock is \
                          %.2f %s. (without reservations)') % \
                (qty, uom_record.name,
                 max(0, prod_obj.virtual_stock_conservative), uom_record.name,
                 max(0, prod_obj.qty_available), uom_record.name)
            warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"

        #update of warning messages
        if warning_msgs:
            warning = {
                'title': _('Configuration Error!'),
                'message': warning_msgs
            }
            res.update({'warning': warning})
        return res
