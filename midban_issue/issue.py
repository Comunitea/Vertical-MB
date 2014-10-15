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


class issue_type(osv.Model):
    """ Master table with differents incidents types."""
    _name = "issue.type"
    _description = "Issue types"
    _columns = {
        'name': fields.char('Type', size=128, required=True),
        'code': fields.char('Code', size=64, readonly=True),  # Internal use
        'reason_ids': fields.one2many('issue.reason', 'type_id', 'Reasons')
    }
    _sql_constraints = [('code', 'unique(code)',
                         'Issue type code alredy exists!')]


class issue_reason(osv.Model):
    """ Master table with differents issue reasons."""
    _name = "issue.reason"
    _description = "Issue reasons"
    _columns = {
        'name': fields.char('Reason', size=128, required=True),
        'code': fields.char('Code', size=64, readonly=True),  # Internal use
        'type_id': fields.many2one('issue.type', 'Type'),
        'stock_location_id': fields.many2one('stock.location',
                                             'Stock location'),
    }
    _sql_constraints = [('code', 'unique(code)',
                         'Issue reason code alredy exists!')]


class product_info(osv.Model):
    """ Table with product information related to issues"""
    _name = "product.info"
    _description = "Product info related to issues"
    _rec_name = 'product_id'
    _columns = {
        'issue_id': fields.many2one('issue', 'Related Issue'),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_qty': fields.float('Quantity', digits_compute=dp
                                    .get_precision('Product UoS'),),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', ),
        'lot_id': fields.many2one('stock.production.lot', 'Lot', ),
        'reason_id': fields.many2one('issue.reason', 'Reason'),
    }


class issue(osv.Model):
    """ General model to manage issues."""
    _name = 'issue'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'create_date'
    _order = 'create_date desc'
    MODELS = [('sale.order', 'Sales'), ('purchase.order', 'Purchases'),
              ('stock.picking', 'Pickings'), ('account.invoice', 'Invoices'),
              ('stock.inventory', 'Inventory')]
    _columns = {
        'create_uid': fields.many2one("res.users", 'User'),
        'create_date': fields.datetime('Date Created'),
        'flow': fields.reference('Associed Flow',
                                 [('sale.order', 'Sales'),
                                  ('purchase.order', 'Purchases')],
                                 size=128),
        'object': fields.reference('Object', MODELS, size=128),
        'origin': fields.char('Issue origin', size=128),
        'res_model': fields.selection(MODELS, 'Res Model'),
        'res_id': fields.integer('Res ID', readonly=True),
        'edi_message': fields.selection([('desadv2', 'DESADV-2'),
                                         ('recadv', 'RECADV')], 'Edi message'),
        'type_id': fields.many2one('issue.type', 'Type'),
        'reason_id': fields.many2one('issue.reason', 'Reason'),
        'affected_fields': fields.char('Affected fields', size=256),
        'affected_partner_id': fields.many2one('res.partner',
                                               'Affected Client'),
        'caused_partner_id': fields.many2one('res.partner', 'Caused Partner'),
        'automatic': fields.boolean('Automatic', readonly=True),
        'product_ids': fields.one2many('product.info', 'issue_id',
                                       'Product information'),
        'solution': fields.char('Solution', size=256),
        'issue_code': fields.char('Issue code', size=256),
        'nbr': fields.integer('NBR')    # Field created for the graph view.
    }
    _defaults = {
        'automatic': False,
        'nbr': 1
    }

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        res = {}
        flow = ''
        caused = False
        affected = False
        if context.get('active_model', '') and \
           context.get('active_id', False):
            model = context['active_model']
            id = context['active_id']
            cur = self.pool.get(model).browse(cr, uid, id)
            if model == 'purchase.order':
                object = model + "," + str(id)
                flow = object
                if cur.partner_id:
                    caused = cur.partner_id.id
                if cur.company_id:
                    affected = cur.company_id.partner_id.id

            elif model == 'sale.order':
                object = model + "," + str(id)
                flow = object
                if cur.partner_id:
                    affected = cur.partner_id.id
                if cur.company_id:
                    caused = cur.company_id.partner_id.id

            # elif model == 'stock.picking.in':
            #     object = "stock.picking," + str(id)
            #     if cur.purchase_id:
            #         flow = 'purchase.order,' + str(cur.purchase_id.id)
            #     if cur.partner_id:
            #         caused = cur.partner_id.id
            #     if cur.warehouse_id and cur.warehouse_id.company_id and \
            #             cur.warehouse_id.company_id.partner_id:
            #         affected = cur.warehouse_id.company_id.partner_id.id
            # elif model == 'stock.picking.out':

            #     object = "stock.picking," + str(id)
            #     if cur.sale_id:
            #         flow = 'sale.order,' + str(cur.sale_id.id)
            #     if cur.partner_id:
            #         affected = cur.partner_id.id
            #     if cur.sale_id and cur.sale_id.shop_id and \
            #             cur.sale_id.shop_id.warehouse_id and \
            #             cur.sale_id.shop_id.warehouse_id.partner_id:
            #         caused = cur.sale_id.shop_id.warehouse_id.partner_id.id
            #     elif cur.company_id:
            #         caused = cur.company_id.partner_id.id

            elif model == 'stock.picking':
                object = "stock.picking," + str(id)
                if cur.purchase_id:
                    flow = 'purchase.order,' + str(cur.purchase_id.id)
                    if cur.partner_id:
                        caused = cur.partner_id.id
                    if cur.warehouse_id and cur.warehouse_id.company_id and \
                            cur.warehouse_id.company_id.partner_id:
                        affected = cur.warehouse_id.company_id.partner_id.id

                if cur.sale_id:
                    flow = 'sale.order,' + str(cur.sale_id.id)
                    if cur.partner_id:
                        affected = cur.partner_id.id
                    if cur.sale_id.shop_id and \
                            cur.sale_id.shop_id.warehouse_id and \
                            cur.sale_id.shop_id.warehouse_id.partner_id:
                        caused = cur.sale_id.shop_id.warehouse_id.partner_id.id
                    elif cur.company_id:
                        caused = cur.company_id.partner_id.id

            res['object'] = object
            res['flow'] = flow
            res['caused_partner_id'] = caused
            res['affected_partner_id'] = affected
        return res

    def create(self, cr, uid, vals, context=None):
        """split object field, e.g. 'purchase.order,12' in res_model and res_id
            for searching"""
        if context is None:
            context = {}
        if vals.get('object', False):
            values = vals['object'].split(',')
            vals['res_model'] = values[0]
            vals['res_id'] = int(values[1])
        return super(issue, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """split object field, e.g. 'purchase.order,12' in res_model and res_id
            for searching"""
        if context is None:
            context = {}
        if vals.get('object', False):
            values = vals['object'].split(',')
            vals['res_model'] = values[0]
            vals['res_id'] = int(values[1])
        return super(issue, self).write(cr, uid, ids, vals, context=context)
