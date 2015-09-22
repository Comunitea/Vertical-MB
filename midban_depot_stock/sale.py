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
from openerp.exceptions import except_orm
from openerp import api, models, fields as fields2


class procurement_group(osv.Model):
    _inherit = 'procurement.group'

    # To pass from sale order to picking, we use it in _picking_assign
    # method of stock.move
    user_id = fields2.Many2one('res.users', 'Comercial', readonly=True)


class sale_order(osv.Model):
    _inherit = 'sale.order'

    _columns = {
        'trans_route_id': fields.related('route_detail_id', 'route_id',
                                         string='Route',
                                         type="many2one",
                                         relation="route",
                                         store=True,
                                         readonly=True),
        'detail_date': fields.related('route_detail_id', 'date',
                                      string='Route Date',
                                      type="date",
                                      relation="route.detail",
                                      store=True,
                                      readonly=True),
        'route_detail_id': fields.many2one('route.detail', 'Detail Route'),
        'date_planned': fields.datetime('Scheduled Date',
                                        select=True,
                                        help="Date propaged to shecduled \
                                              date of related picking"),
    }

    @api.onchange('route_detail_id')
    @api.multi
    def onchange_route_detail_id(self):
        """
        Try to find a route detail model of the closest day scheduled in a
        customer list of a detail model and assign it, also assign de date
        planned with the detail date
        """
        if self.route_detail_id:
            self.date_planned = self.route_detail_id.date + " 19:00:00"

    def _get_date_planned(self, cr, uid, order, line, start_date,
                          context=None):
        """
        Overwrited in order to pass to the min_date field of related picking
        the date setted in the new date_planned field. From procurement pass to
        move throught date_expected field.
        """
        res = super(sale_order, self)._get_date_planned(cr, uid, order, line,
                                                        start_date,
                                                        context=context)

        date_planned = order.date_planned and order.date_planned or res
        return date_planned

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        """
        When changing the partner the asociated route detail is filled.
        If no detailed found, get a warning when is configured this way with
        check sale orders.
        When we match a detailed route of closest day we put the date in date
        planned field to pass it to the picking, if no detail matched we put
        default date planned.
        """
        res = super(sale_order, self).onchange_partner_id(cr,
                                                          uid,
                                                          ids,
                                                          part,
                                                          context=context)
        partner_t = self.pool.get('res.partner')
        part = partner_t.browse(cr, uid, part, context=context)
        # Get next detail of a delivery route
        if not res['value'].get('route_detail_id', False):
            detail_obj = part.get_next_route_detail(route_type='delivery')
            if detail_obj:
                res['value']['route_detail_id'] = detail_obj.id
                res['value']['date_planned'] = detail_obj.date + \
                    " 19:00:00"
            else:
                res['value']['route_detail_id'] = False
                res['value']['date_planned'] = False

        if part and not res['value'].get('route_detail_id', False):
            t_config = self.pool.get('ir.config_parameter')
            param_value = t_config.get_param(cr, uid, 'check.sale.order',
                                             default='True')
            if param_value == 'True':
                res['value']['route_detail_id'] = False
                res['value']['date_planned'] = False
                res['warning'] = {'title': _('Warning!'),
                                  'message': _('No delivery routes assigned in\
                                   the customer. You will not confirm the \
                                   order')}
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
        # res['trans_route_id'] = order.trans_route_id and \
        #     order.trans_route_id.id or False
        res['route_detail_id'] = order.route_detail_id and \
            order.route_detail_id.id or False
        return res

    def _get_mandatory_camera(self, cr, uid, context=None):
        if context is None:
            context = {}
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'mandatory.camera',
                                         default='True')
        return True if param_value == 'True' else False

    def action_ship_create(self, cr, uid, ids, context=None):
        """
        Overwrited to check if there is a detail route assigned when this
        behaivor is configured. If no detail route assigned and check sale
        orders is configured it will raise an error.
        If detail route (of delivery type) is assigned we find the customer
        in the customer list and write the orderl, if not customer scheduled
        for the selected detail we create it.
        """
        if context is None:
            context = {}
        # If not detail route asigned raise an error if it is configured
        t_config = self.pool.get('ir.config_parameter')
        param_value = t_config.get_param(cr, uid, 'check.sale.order',
                                         default='True')
        for order in self.browse(cr, uid, ids, context=context):
            if not order.route_detail_id and param_value == 'True':
                raise except_orm(_('Error'),
                                 _('Detail of route must be assigned to \
                                    confirm the order'))
            if order.route_detail_id:
                if order.route_detail_id.route_type != 'delivery':
                    route_name = order.route_detail_id.name_get()[0][1]
                    raise except_orm(_('Error'),
                                     _('Detail route %s must be of delivery \
                                        type' % route_name))
                selected_record = False
                for record in order.route_detail_id.customer_ids:
                    if record.customer_id.id == order.partner_id.id:
                        selected_record = record
                        break
                if selected_record:
                    selected_record.write({'sale_id': order.id})
                else:
                    vals = {
                        'detail_id': order.route_detail_id.id,
                        'customer_id': order.partner_id.id,
                        'sale_id': order.id,
                    }
                    self.pool.get('customer.list').create(cr, uid, vals,
                                                          context)
        res = super(sale_order, self).action_ship_create(cr, uid, ids,
                                                         context=context)
        return res

    @api.multi
    def write(self, vals):
        """
        Overwrited in order to write the read_only date_planned when a
        detail_route is setted.
        """
        for order in self:
            if vals.get('route_detail_id', False):
                t_detail = self.env['route.detail']
                detail_obj = t_detail.browse(vals['route_detail_id'])
                detail_date = detail_obj.date + " 19:00:00"
                order.date_planned = detail_date
        res = super(sale_order, self).write(vals)
        return res

    def _prepare_procurement_group(self, cr, uid, order, context=None):
        """
        In order to pass the comercial to the picking
        """
        sup = super(sale_order, self)
        res = sup._prepare_procurement_group(cr, uid, order, context=context)
        res['user_id'] = order.user_id.id
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
                                             qty=qty, uom=uom,
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
        cross_dock_product = prod_obj.is_cross_dock
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

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False,
                                         context=None):
        """
        #TODO!
        """
        res = super(sale_order_line, self).\
            _prepare_order_line_invoice_line(cr, uid, line, account_id,
                                             context)
        if not line.invoiced:
            res['price_unit'] = line.price_unit
        return res
