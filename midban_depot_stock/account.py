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
import openerp.addons.decimal_precision as dp
from openerp import api

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _columns = {
        'stock_move_id': fields.many2one('stock.move', 'Stock Move'),
        'second_uom_id': fields.many2one("product.uom", "Second Uom",
                                         readonly=True),
        'quantity_second_uom': fields.\
            float("Qty Second Uom", readonly=True,
                  digits_compute=dp.get_precision('Product Unit of Measure'))
    }

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='',
                          type='out_invoice', partner_id=False,
                          fposition_id=False, price_unit=False,
                          currency_id=False, company_id=None):
        res = super(account_invoice_line, self).\
            product_id_change(product, uom_id, qty=qty, name=name, type=type,
                              partner_id=partner_id, fposition_id=fposition_id,
                              price_unit=price_unit, currency_id=currency_id,
                              company_id=company_id)

        if res.get('value', False):
            res['value']['second_uom_id'] = False
            res['value']['quantity_second_uom'] = 0.0
        return res

    @api.multi
    def uos_id_change(self, product, uom, qty=0, name='', type='out_invoice',
                      partner_id=False, fposition_id=False, price_unit=False,
                      currency_id=False, company_id=None):
        res = super(account_invoice_line, self).\
            uos_id_change(product, uom, qty=qty, name=name, type=type,
                          partner_id=partner_id, fposition_id=fposition_id,
                          price_unit=price_unit, currency_id=currency_id,
                          company_id=company_id)
        if res.get('value', False):
            res['value']['second_uom_id'] = False
            res['value']['quantity_second_uom'] = 0.0
        return res


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _get_order_pick_ids(self, cr, uid, ids, field_names, args,
                            context=None):
        """
        Function that returns the related picking, sales or purchases to the
        invoice, in order to can display it from a button.
        """
        if context is None:
            context = {}
        res = {}
        pick_ids = set()
        sale_ids = set()
        purchase_ids = set()
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {'sale_ids': [], 'pick_ids': []}
            for line in invoice.invoice_line:
                if line.stock_move_id and line.stock_move_id.picking_id:
                    pick_ids.add(line.stock_move_id.picking_id.id)
                    if line.stock_move_id.picking_id.sale_id:
                        sale_ids.add(line.stock_move_id.picking_id.sale_id.id)
                    if line.stock_move_id.picking_id.purchase_id:
                        po_id = line.stock_move_id.picking_id.purchase_id.id
                        purchase_ids.add(po_id)
            res[invoice.id]['pick_ids'] = list(pick_ids)
            res[invoice.id]['sale_ids'] = list(sale_ids)
            res[invoice.id]['purchase_ids'] = list(purchase_ids)
        return res

    _columns = {
        'sale_ids': fields.function(_get_order_pick_ids, type="one2many",
                                    multi="orders_picks",
                                    relation='sale.order',
                                    string="Related Sales",
                                    readonly=True),
        'pick_ids': fields.function(_get_order_pick_ids, type="one2many",
                                    multi="orders_picks",
                                    relation='stock.picking',
                                    string="Related Sales",
                                    readonly=True),
        'purchase_ids': fields.function(_get_order_pick_ids, type="one2many",
                                        multi="orders_picks",
                                        relation='purchase.order',
                                        string="Related Sales",
                                        readonly=True)
    }

    def action_view_sales(self, cr, uid, ids, context=None):
        """
        Button method to view related sales
        """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'sale', 'action_orders')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        sale_ids = []
        for invoice in self.browse(cr, uid, ids, context=context):
            sale_ids += [sale.id for sale in invoice.sale_ids]
        #choose the view_mode accordingly
        if len(sale_ids) > 1:
            result['domain'] = \
                "[('id','in',[" + ','.join(map(str, sale_ids)) + "])]"
        elif sale_ids:
            res = mod_obj.get_object_reference(cr, uid, 'sale',
                                               'view_order_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = sale_ids and sale_ids[0] or False
        else:
            return False
        return result

    def action_view_pickings(self, cr, uid, ids, context=None):
        """
        Button method to view related action_get_pickings
        """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'stock',
                                              'action_picking_tree_all')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        pick_ids = []
        for invoice in self.browse(cr, uid, ids, context=context):
            pick_ids += [sale.id for sale in invoice.pick_ids]
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = \
                "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif pick_ids:
            res = mod_obj.get_object_reference(cr, uid, 'stock',
                                               'view_picking_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        else:
            return False
        return result

    def action_view_purchases(self, cr, uid, ids, context=None):
        """
        Button method to view related action_get_pickings
        """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'purchase',
                                              'purchase_form_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        po_ids = []
        for invoice in self.browse(cr, uid, ids, context=context):
            po_ids += [purchase.id for purchase in invoice.purchase_ids]
        #choose the view_mode accordingly
        if len(po_ids) > 1:
            result['domain'] = \
                "[('id','in',[" + ','.join(map(str, po_ids)) + "])]"
        elif po_ids:
            res = mod_obj.get_object_reference(cr, uid, 'purchase',
                                               'purchase_order_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = po_ids and po_ids[0] or False
        else:
            return False
        return result
