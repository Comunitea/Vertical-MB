# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from openerp.osv import osv

#----------------------------------------------------------
# Stock Picking
#----------------------------------------------------------
class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _description = "Picking List"

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
        invoice_vals, context=None):
        """Overwrite to add move_id reference"""
        res = super(stock_picking, self)._prepare_invoice_line(cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=context)
        res.update({
            'move_id': move_line.id,
        })
        return res

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        '''Return ids of created invoices for the pickings'''
        res = super(stock_picking,self).action_invoice_create(cr, uid, ids, journal_id, group, type, context=context)
        # if type == 'in_refund':
        #     for inv in self.pool.get('account.invoice').browse(cr, uid, res, context=context):
        #         for ol in inv.invoice_line:
        #             if ol.product_id:
        #                 #Only if the destination location is within a company
        #                 if ol.move_line_ids[0].location_dest_id.company_id:
        #                     oa = ol.product_id.property_stock_account_output and ol.product_id.property_stock_account_output.id
        #                     if not oa:
        #                         oa = ol.product_id.categ_id.property_stock_account_output_categ and ol.product_id.categ_id.property_stock_account_output_categ.id
        #                     if oa:
        #                         fpos = ol.invoice_id.fiscal_position or False
        #                         a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
        #                         self.pool.get('account.invoice.line').write(cr, uid, [ol.id], {'account_id': a})
        #
        # elif type == 'in_invoice':
        #     for inv in self.pool.get('account.invoice').browse(cr, uid, res, context=context):
        #         for ol in inv.invoice_line:
        #             if ol.product_id:
        #                 #Only if the destination location is within a company
        #                 if ol.move_line_ids[0].location_dest_id.company_id:
        #                     oa = ol.product_id.property_stock_account_input and ol.product_id.property_stock_account_input.id
        #                     if not oa:
        #                         oa = ol.product_id.categ_id.property_stock_account_input_categ and ol.product_id.categ_id.property_stock_account_input_categ.id
        #                     if oa:
        #                         fpos = ol.invoice_id.fiscal_position or False
        #                         a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
        #                         self.pool.get('account.invoice.line').write(cr, uid, [ol.id], {'account_id': a})
        return res