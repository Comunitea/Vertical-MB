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
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from openerp.tools.float_utils import float_round, float_compare, float_is_zero
from openerp.api import Environment
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import threading
import logging
_logger = logging.getLogger(__name__)


class QualitativeNote(models.Model):
    """ New model to get a qualitative comment un sale order lines"""

    _name = 'qualitative.note'
    _rec_name = 'code'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    price_udv = fields.Float('Price UdV',
                             digits_compute=dp.get_precision('Product Price'),
                             required=True)
    do_onchange = fields.Boolean('Do onchange', default=True)
    q_note = fields.Many2one('qualitative.note', 'Qualitative Comment')
    detail_note = fields.Char('Details', size=256)
    product_code = fields.Char('Reference', size=32)

    # def unlink(self):
    #     res = super(sale_order, self).unlink()

    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product,
                                  qty=0, uom=False, qty_uos=0, uos=False,
                                  name='', partner_id=False, lang=False,
                                  update_tax=True,
                                  date_order=False,
                                  packaging=False,
                                  fiscal_position=False, flag=False,
                                  warehouse_id=False, context=None):
        """
        We overwrite with this name because of midban_depot_stock dependency.
        Is defined in sale_stock module
        """
        if context is None:
            context = {}
        fpos = fiscal_position
        sup = super(sale_order_line, self)
        res = sup.product_id_change_with_wh(cr, uid, ids, pricelist,
                                            product, qty=qty, uom=uom,
                                            qty_uos=qty_uos, uos=uos,
                                            name=name,
                                            partner_id=partner_id,
                                            lang=lang,
                                            update_tax=update_tax,
                                            date_order=date_order,
                                            packaging=packaging,
                                            fiscal_position=fpos,
                                            flag=flag,
                                            warehouse_id=warehouse_id,
                                            context=context)
        if not product:
            return res
        prod_obj = self.pool.get('product.product').browse(cr, uid,
                                                           product,
                                                           context=context)
        t_ir =  self.pool.get('ir.model.data')
        dom_pricelist = t_ir.xmlid_to_res_id(cr, uid, 'midban_product.list1')
        uom_id_first = False if dom_pricelist == pricelist else True
        # SI cliente a domicilio traermos primero la unidad mas pequeña
        product_udv_ids = prod_obj.get_sale_unit_ids(uom_id_first)
        # uom_domain = [('id', 'in', product_udv_ids)]
        # res['domain'] = {'product_uos': uom_domain}
        res['value']['product_uos'] = \
            product_udv_ids and product_udv_ids[0] or False
        res['value']['product_uom'] = prod_obj.uom_id.id
        res['value']['product_uos_qty'] = 1.0

        #if prod_obj.box_discount:
        #    res['value']['discount'] = prod_obj.box_discount
        # import ipdb; ipdb.set_trace()
        #
        # log_unit = prod_obj.get_uos_logistic_unit(uos)
        # # Unit es la caja logistica para apolo (llamada base)
        # if log_unit == 'base' and prod_obj.log_base_discount:
        #     res['value']['discount'] = prod_obj.log_base_discount
        # elif log_unit == 'unit' and prod_obj.log_unit_discount:
        #     res['value']['discount'] = prod_obj.log_unit_discount
        # elif log_unit == 'box' and prod_obj.log_box_discount:
        #     res['value']['discount'] = prod_obj.log_box_discount
        return res

    @api.onchange('product_code')
    def product_code_onchange(self):
        """
        We change the product_uom_qty
        """
        code = self.product_code
        if code:
            pr_ids = self.env['product.product'].search([('default_code', '=', code)])
            if len(pr_ids) == 1:
                self.product_id = pr_ids[0]
            else:
                self.product_code = False

    @api.onchange('product_uos_qty')
    def product_uos_qty_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            if self.do_onchange:
                #qty = self.product_uos_qty
                uos_id = self.product_uos.id
                qty = float_round(self.product_uos_qty,
                                  precision_rounding=self.product_uos.rounding,
                                  rounding_method='UP')
                self.product_uos_qty = qty
                #conv = product.get_unit_conversions(qty, uos_id)
                # base, unit, or box
                #log_unit = product.get_uom_logistic_unit()
                #self.product_uom_qty = conv[log_unit]
                self.product_uom_qty = product.uos_qty_to_uom_qty(qty, uos_id)
            else:
                self.do_onchange = True

    @api.onchange('product_uos')
    def product_uos_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            # Change Uom Qty
            uos_id = self.product_uos.id
            uos_qty = self.product_uos_qty
            # conv = product.get_unit_conversions(uos_qty, uos_id)
            log_unit = product.get_uos_logistic_unit(uos_id)
            # self.product_uom_qty = conv[log_unit]
            self.product_uom_qty = product.uos_qty_to_uom_qty(uos_qty, uos_id)
            # Unit es la caja logistica para apolo (llamada base)
            if log_unit == 'base' and product.log_base_discount:
                self.discount = product.log_base_discount
            elif log_unit == 'unit' and product.log_unit_discount:
                self.discount = product.log_unit_discount
            elif log_unit == 'box' and product.log_box_discount:
                self.discount =product.log_box_discount

            # Calculate prices
            uom_pu, uos_pu = product.get_uom_uos_prices(uos_id,
                                                        custom_price_unit=self.
                                                        price_unit)
            # Avoid trigger onchange_price_udv, because is already calculed
            if uos_pu != self.price_udv:
                self.do_onchange = False

            self.price_udv = uos_pu
            # self.price_unit = uom_pu

    @api.multi
    def write(self, vals):
        """
        Overwrite to recalculate the product_uom_qty and product_uom
        because they are readonly in the view and the onchange
        value is not in the vals dict
        """
        res = False
        for line in self:
            if vals.get('product_id', False):
                prod = self.env['product.product'].browse(vals['product_id'])
            else:
                prod = line.product_id
            if prod:
                uos_qty = vals.get('product_uos_qty', False) and \
                    vals['product_uos_qty'] or line.product_uos_qty
                uos_id = vals.get('product_uos', False) and \
                    vals['product_uos'] or line.product_uos.id
                vals['product_uom_qty'] = uos_qty / prod._get_factor(uos_id)
                vals['product_uom'] = prod.uom_id.id
            res = super(sale_order_line, line).write(vals)
        return res

    @api.model
    def create(self, vals):
        """
        Overwrite to recalculate the product_uom_qty and product_uos_qty
        because of sometimes they are readonly in the view and the onchange
        value is not in the vals dict
        """
        if vals.get('product_id', False):
            prod = self.env['product.product'].browse(vals['product_id'])
            uos_qty = vals.get('product_uos_qty', False) and \
                vals['product_uos_qty'] or 0.0
            uos_id = vals.get('product_uos', False) and \
                vals['product_uos'] or False
            #conv = prod.get_unit_conversions(uos_qty, uos_id)
            #log_unit = prod.get_uom_logistic_unit()  # base, unit, or box
            #vals['product_uom_qty'] = conv[log_unit]
            vals['product_uom_qty'] = uos_qty / prod._get_factor(uos_id)
            vals['product_uom'] = prod.uom_id.id
        res = super(sale_order_line, self).create(vals)
        return res

    def no_onchange_price_unit(self, product_id, price_unit, product_uos):
        """
        We change the product_uom_qty
        """
        product = product_id
        if product:
            prod = self.env['product.product'].browse(product)
            uos = product_uos
            uos_id = product_uos
            uom_pu, uos_pu = \
                prod.get_uom_uos_prices(uos_id,
                                           custom_price_unit=price_unit)
            # Avoid trigger onchange_price_udv, because is already calculed
            price_udv = uos_pu
        return price_udv

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            if self.do_onchange:
                uos = self.product_uos
                uos_id = uos.id
                uom_pu, uos_pu = \
                    product.get_uom_uos_prices(uos_id,
                                               custom_price_unit=self.
                                               price_unit)
                # Avoid trigger onchange_price_udv, because is already calculed
                if uos_pu != self.price_udv:
                    self.do_onchange = False
                self.price_udv = uos_pu
            else:
                self.do_onchange = True

    @api.onchange('price_udv')
    def price_udv_onchange(self):
        """
        We change the product_uom_qty
        """
        product = self.product_id
        if product:
            if self.do_onchange:
                uos_id = self.product_uos.id
                # Calculate prices
                uom_pu, uos_pu = \
                    product.get_uom_uos_prices(uos_id,
                                               custom_price_udv=self.price_udv)
                # Avoid trigger onchange_price_unit, already calculed
                if uom_pu != self.price_unit:
                    self.do_onchange = False
                    self.price_unit = uom_pu
            else:
                self.do_onchange = True


class sale_order(models.Model):
    _inherit = 'sale.order'

    customer_comment = fields.Text('Customer comment',
                                   related='partner_id.comment')
    # user_id2 = fields.Many2one('res.users', 'User')

    # @api.model
    # def create(self, vals):
    #     """
    #     Overwrited in order to write user that create the sale order.
    #     """
    #     vals.update({'user_id2': self._uid})
    #     res = super(sale_order, self).create(vals)
    #     return res

    def change_price_vals(self, vals):
        if len(self) > 1:
            return vals
        else:
            if  vals.get('chanel', False) != 'tablet' and self.chanel != 'tablet':
                return vals
        sol_obj = self.env['sale.order.line']
        pricelist = vals.get('pricelist_id', False) or self.pricelist_id and self.pricelist_id.id
        partner_id = vals.get('partner_id', False) or self.partner_id and self.partner_id.id
        if vals.get('order_line', False):
            for line_est in vals['order_line']:
                if line_est[0] in [0, 1]:
                    line=line_est[2]

                    if line_est[0] == 1:
                        line_obj = sol_obj.browse (line_est[1])
                        product_id = line.get('product_id', False) or line_obj.product_id and line_obj.product_id.id
                        product_uom_qty = line.get('product_uom_qty', False) or line_obj.product_uom_qty
                        product_uos_qty = line.get('product_uom_qty', False) or line_obj.product_uos_qty
                        product_uom = line.get('product_uom', False) or line_obj.product_uom and line_obj.product_uom.id
                        product_uos = line.get('product_uos', False) or line_obj.product_uos and line_obj.product_uos.id
                    else:
                        product_id = line.get('product_id', False)
                        product_uom_qty = line.get('product_uom_qty', False)
                        product_uom = line.get('product_uom', False)
                        product_uos = line.get('product_uos', False)
                        product_uos_qty = line.get('product_uos_qty', False)

                    vals_mod = sol_obj.product_id_change_with_wh(pricelist, product_id, product_uom_qty,
                                                                product_uom, line.get('product_uos_qty', False),
                                                                product_uos, partner_id = partner_id)
                    if vals_mod['value'].get('discount', False):
                        line['discount'] = vals_mod['value']['discount']
                    if vals_mod['value'].get('tourism', False):
                        line['tourism'] = vals_mod['value']['tourism']
                    if vals_mod['value'].get('price_unit', False):
                        if line.get('price_unit', False) and not float_is_zero(line['price_unit'],
                                         precision_digits=2):  # Si es cero
                            # no se cambia el precio
                            line['price_unit'] = vals_mod['value']['price_unit']
                            res = sol_obj.no_onchange_price_unit(product_id,
                                                                line['price_unit'],product_uos)
                            line['price_udv'] = res
        return vals

    #FUNCIONES PARA LLAMAR DESDE TABLET
    @api.model
    def create_and_confirm(self, vals):
        if vals.get('chanel', False) == 'tablet':
            vals = self.change_price_vals(vals)
        #vals.update({'user_id2': self._uid})
        res = self.create(vals)
        if res:
            res.action_button_confirm()
        return res

    @api.model
    def easy_change(self, vals):
        self.cancel_sale_to_draft()
        vals = self.change_price_vals(vals)
        res =  self.write(vals)
        if res:
            self.action_button_confirm()
        return res


    @api.model
    def write(self, vals):
        #if vals.get('chanel', False) == 'tablet':
        vals = self.change_price_vals(vals)
        res = super(sale_order, self).write(vals)
        if res:
            self.recalculate_taxes()
        return res


    @api.model
    def check_duplicate(self, vals):
        date_from =  time.strftime("%x")
        domain = [('partner_shipping_id','=',
                   vals.get('partner_shipping_id', False)),
                ('partner_id', '=', vals.get('partner_id',False)),
                ('date_order', '>=', date_from)]
        ids = self.search(domain)

        if len(ids):
            products_vals = [vals_line[2]['product_id'] for vals_line in vals[
                    'order_line']]
            for so in ids:
                products = [line.product_id.id for line in so.order_line]
                if set(products) == set(products_vals):
                    user = self.env['res.users'].browse(vals.get('user_id',
                                                                 False))
                    partner = self.env['res.partner'].browse(vals.get(
                                                                 'partner_id', False))
                    print "***************************************************"
                    print "** INTENTANDO INTRODUCIR PEDIDO DUPLICADO   *******"
                    print u" Cliente: %s  //  Comercial: %s"%(
                        partner and partner.comercial, user and user.name)
                    print "***************************************************"
                    return so
            else:
                return []
        else:
            return []

    @api.model
    def create(self, vals):
        if vals.get('chanel', False) == 'tablet':
            res = self.check_duplicate(vals)
            if len(res):
                return res
            vals = self.change_price_vals(vals)
        #vals.update({'user_id2': sel>=f._uid})
        res = super(sale_order, self).create(vals)
        if res:
            res.recalculate_taxes()
        return res

    @api.one
    @api.model
    def recalculate_taxes(self):
        if self.chanel == 'tablet' and self.fiscal_position:
            print "pedido de tablet"
            print "Recalcula impuestos"
            for line in self.order_line:
                line.tax_id = self.fiscal_position.map_tax(line.tax_id)

    @api.multi
    def action_ship_create(self):
        """
        It compares lines and shows an error if it found many lines of the
        same product with different units of measure selected.
        """
        t_line = self.env['sale.order.line']
        # TODO COMETNAR Y PERMITIRLO, gestionar en do_prepare_partial caso de
        # 2 movimientos en 1 misma operación, debería separarse en operaciones
        # por unidad de venta.
        for order in self:
            #PARA CALCULAR PROMOS SIEMPRE

            order.apply_promotions()
            for line in order.order_line:
                domain = [('order_id', '=', order.id),
                          ('product_id', '=', line.product_id.id),
                          ('id', '!=', line.id),
                          ('product_uos', '!=', line.product_uos.id)]
                line_objs = t_line.search(domain)
                if line_objs:
                    raise except_orm(_('Error'),
                                     _("You can't sale product %s in \
                                     different sale units")
                                     % line_objs[0].product_id.name)

        res = super(sale_order, self).action_ship_create()

        sm_obj = self.env['stock.move']
        for order in self:
            pick_ids = []
            for so in self.browse(order.id):
                for pick in so.picking_ids:
                    if pick.picking_type_id.code == 'outgoing':
                        out_pick = pick
            sale_line_ids = self.env['sale.order.line']
            if order.procurement_group_id:
                for proc in order.procurement_group_id.procurement_ids:
                    if proc.product_qty <= 0:
                        #print "A CANCELAR "
                        procurement = proc
                        proc.cancel()
                        proc.move_ids.unlink()
                        sale_line_ids += proc.sale_line_id
                if len(sale_line_ids):
                    order.generate_returns(sale_line_ids, out_pick)
        return res

    @api.one
    def generate_returns(self, sale_line_ids, out_pick):
        sol_obj = self.env['sale.order.line']
        sm_obj = self.env['stock.move']
        data_obj = self.env['ir.model.data']
        #location_dest_id = data_obj.get_object_reference('stock_picking_review', 'stock_location_returns')[1]
        moves = self.env['stock.move']
        picking_type = out_pick.picking_type_id.return_picking_type_id
        for line in sale_line_ids:
            warehouse = line.order_id.warehouse_id
            location_id = line.order_id.partner_shipping_id.property_stock_customer.id

            new_move_id = sm_obj.create({
                'product_id': line.product_id.id,
                'product_uom_qty': -line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'product_uos': line.product_uos.id,
                'product_uos_qty': -line.product_uos_qty,
                #'picking_id': new_picking,
                'state': 'draft',
                'location_id': location_id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'picking_type_id': picking_type.id,
                'warehouse_id': line.order_id.warehouse_id.id,
                'procure_method': 'make_to_stock',
                'restrict_lot_id': False,
                'move_dest_id': False,
                'invoice_state': '2binvoiced',
                'name': line.product_id.name,
                'group_id': out_pick.group_id.id
            })
            moves += new_move_id

        if len(moves):
            new_picking = out_pick.copy({
                'move_lines': [],
                'picking_type_id': picking_type.id,
                'state': 'draft'
            })

            moves.write({'picking_id': new_picking.id})
            new_picking.action_confirm()
            new_picking.action_assign()

    @api.one
    def action_button_confirm_thread(self):
        _logger.debug("CMNT PREPARA EL HILO ")
        thread = threading.Thread(
            target=self._action_button_confirm_thread)
        thread.start()
        return True

    # @api.model
    # def action_button_confirm(self):
    #     print "Confirm heredado"
    #     if self.chanel == 'tablet':
    #         print "CONFIRMO DESDE TABLET"
    #         self.apply_promotions()
    #     return super(sale_order, self).action_button_confirm()

    @api.model
    @api.one
    def _action_button_confirm_thread(self):
        _logger.debug("CMNT ENTRA EN EL HILO!!!!!!!!!")
        new_cr = self.pool.cursor()
        with Environment.manage():
            uid, context = self.env.uid, self.env.context
            env = Environment(new_cr, uid, context)
            try:
                env['sale.order'].browse(self.id).action_button_confirm()

            except Exception, e:
                new_cr.rollback()
                new_cr.close()
                _logger.debug("CMNT ERROR EN EL HILO!!!!!!!!! %s", str(e))
            new_cr.commit()
            new_cr.close()
            return {}
            # records = self._get_followers(cr, uid, ids, None, None, context=context)
            # followers = records[ids[0]]['message_follower_ids']
            # self.message_post(cr, uid, ids, "Error en la confirmación de pedido: " + ValueError,
            #         subtype='mt_comment',
            #         partner_ids=followers,
            #         context=context)
