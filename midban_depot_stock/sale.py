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
from datetime import datetime, timedelta


class sale_order(osv.Model):
    _inherit = 'sale.order'

    def _get_next_working_date(self, cr, uid, context=None):
        """
        Returns the next working day date respect today
        """
        today = datetime.now()
        week_day = today.weekday()  # Monday 0 Sunday 6
        delta = 1
        if week_day == 4:
            delta = 3
        elif week_day == 5:
            delta = 2
        new_date = today + timedelta(days=delta or 0.0)
        date_part = datetime.strftime(new_date, "%Y-%m-%d")
        res = datetime.strptime(date_part + " " + "22:59:59",
                                "%Y-%m-%d %H:%M:%S")
        return res

    _columns = {
        'trans_route_id': fields.many2one('route', 'Transport Route',
                                          domain=[('state', '=', 'active')],
                                          readonly=True, states={'draft':
                                                                 [('readonly',
                                                                   False)],
                                                                 'sent':
                                                                 [('readonly',
                                                                   False)]}),
        'date_planned': fields.datetime('Scheduled Date', required=True,
                                        select=True,
                                        help="Date propaged to shecduled \
                                              date of related picking"),
    }
    _defaults = {
        'date_planned': _get_next_working_date,
    }

    def _get_date_planned(self, cr, uid, order, line, start_date,
                          context=None):
        """
        Overwrited in order to pass to the min_date field of related picking
        the date setted in the new date_planned field. From procurement pass to
        move throught date_expected field.
        """
        date_planned = order.date_planned
        return date_planned

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
        if not res['value'].get('trans_route_id', []):
            if part.trans_route_id:
                res['value']['trans_route_id'] = part.trans_route_id.id
        return res

    def _prepare_order_line_procurement(self, cr, uid, order, line,
                                        group_id=False, context=None):
        """
        Overwrited
        Write the route to the procurements froma sale order lines,
        the drop codes will be assigned later.
        """
        res = super(sale_order, self).\
            _prepare_order_line_procurement(cr, uid, order, line,
                                            group_id=group_id, context=context)
        res['trans_route_id'] = order.trans_route_id and \
            order.trans_route_id.id or False
        return res

    def action_ship_create(self, cr, uid, ids, context=None):
        """
        Overwrited to assign a drop code for each order, an update the next_dc
        field in transport route model.
        """
        if context is None:
            context = {}
        procurement_obj = self.pool.get('procurement.order')
        res = super(sale_order, self).action_ship_create(cr, uid, ids,
                                                         context=context)
        for order in self.browse(cr, uid, ids, context=context):
            if order.procurement_group_id:
                proc_ids = \
                    [x.id for x in order.procurement_group_id.procurement_ids]
                if proc_ids:
                    dc = order.trans_route_id and \
                        order.trans_route_id.next_dc or 0
                    vals = {'drop_code': dc}
                    procurement_obj.write(cr, uid, proc_ids, vals, context)
            if order.trans_route_id:
                next_dc = order.trans_route_id.next_dc
                order.trans_route_id.write({'next_dc': next_dc + 1})
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
        """
        Check virtual stock conservative, if fresh or ultrafresh product,
        or cross_dock route marked, avoid launch a warning.
        """
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
                                             flag=flag,
                                             warehouse_id=warehouse_id,
                                             context=context)

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
        fresh_product = prod_obj.product_class in ['fresh', 'ultrafresh']
        # Check if it have cross-dock route marked
        cross_dock_product = False
        # TODO comprobar booleano en ruta, mejor x si hay varios almacenes
        if fresh_product or cross_dock_product:
            del res['warning']  # Delete warning from super
        if compare_qty == -1 and not fresh_product and not cross_dock_product:
            warn_msg = _('You plan to sell %.2f %s but you only have %.2f %s \
                          available in conservative !\nThe real stock is \
                          %.2f %s. (without reservations)') % \
                (qty, uom_record.name,
                 max(0, prod_obj.virtual_stock_conservative), uom_record.name,
                 max(0, prod_obj.qty_available), uom_record.name)
            warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"

        # update of warning messages
        if warning_msgs:
            warning = {
                'title': _('Configuration Error!'),
                'message': warning_msgs
            }
            res.update({'warning': warning})
        return res
