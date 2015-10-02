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
from openerp.osv import fields, osv
from openerp import api
from openerp.tools.translate import _


class create_tag_wizard(osv.TransientModel):
    _name = "create.tag.wizard"

    def default_get(self, cr, uid, fields, context=None):
        res = super(create_tag_wizard, self).default_get(cr, uid, fields,
                                                         context=context)
        if context is None:
            context = {}
        t_item = self.pool.get('tag.item')
        item_ids = []
        t_task = self.pool.get('stock.task')
        t_pick = self.pool.get('stock.picking')
        if context.get('active_model', False) and \
                context.get('active_id', False):
            active_id = context['active_id']
            operation_ids = []
            if context['active_model'] == 'stock.task':
                task_obj = t_task.browse(cr, uid, active_id, context=context)
                operation_ids = task_obj.operation_ids
            elif context['active_model'] == 'stock.picking':
                pick_obj = t_pick.browse(cr, uid, active_id, context=context)
                operation_ids = pick_obj.pack_operation_ids
            for op in operation_ids:
                vals = {}
                prod = op.operation_product_id and \
                    op.operation_product_id or False
                if prod:
                    lot_id = op.lot_id and op.lot_id.id or False
                    if not lot_id:
                        lot_id = op.package_id and \
                            (op.package_id.packed_lot_id and
                             op.package_id.packed_lot_id.id or False) or\
                            False
                    vals = {
                        'product_id': prod.id,
                        'default_code': prod.default_code,
                        'lot_id': lot_id,
                        'removal_date': op.lot_id and op.lot_id.removal_date or
                        False,
                        'package_id': op.result_package_id and
                        op.result_package_id.id or False
                    }
                    # if op.picking_id.picking_type_code == 'internal':
                    print_tag = True
                    # Check if we are inreposition task if is needed a tag
                    if lot_id and context['active_model'] == 'stock.task':
                        # Reception operation, Suppliers to input location
                        if not op.package_id and op.result_package_id:
                            pass
                        else:
                            pack = op.location_dest_id.get_package_of_lot(lot_id)
                            if pack:
                                print_tag = False
                    if print_tag:
                        item_ids.append(t_item.create(cr, uid, vals, context))
        res.update({'tag_ids': item_ids})
        if context.get('show_print_report', False):
            res.update({'show_print_report': True})
        if item_ids:
            res.update({'tag_exist': True})
        return res

    _columns = {
        'tag_ids': fields.one2many('tag.item', 'wizard_id', 'Tags'),
        'show_print_report': fields.boolean('Show', readonly=True),
        'printed': fields.boolean('Printed', readonly=True),
        'tag_exist': fields.boolean('TAg Exists?')
    }

    def print_tags(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        tag_ids = []
        t_tag = self.pool.get('tag')
        for item in wzd_obj.tag_ids:
            vals = {
                'product_id': item.product_id.id,
                'default_code': item.default_code or False,
                'lot_id': item.lot_id and item.lot_id.id or False,
                'removal_date': item.removal_date,
                'package_id': item.package_id and item.package_id.id or False
            }
            tag_ids.append(t_tag.create(cr, uid, vals, context))
        ctx = dict(context)
        ctx['active_ids'] = tag_ids
        ctx['active_model'] = 'tag'
        wzd_obj.write({'printed': True})
        return self.pool.get("report").\
            get_action(cr, uid, [],
                       'midban_depot_stock.report_stock_tag', context=ctx)

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = dict(context)
        wzd_obj = self.browse(cr, uid, ids[0], context)
        if wzd_obj.tag_ids and not wzd_obj.printed:
            raise osv.except_osv(_('Error!'), _("You must print labels first"))

        if context.get('active_model', False) == 'stock.task':
            task_id = context.get('active_id', False)
            if task_id:
                ctx['active_ids'] = [task_id]
                ctx['active_model'] = 'stock.task'
            return self.pool.get("report").\
                get_action(cr, uid, [],
                           'midban_depot_stock.report_operations_list',
                           context=ctx)
        return


class tag_item(osv.TransientModel):
    _name = "tag.item"

    _columns = {
        'wizard_id': fields.many2one('create.tag.wizard', 'Wizard',
                                     ondelete="cascade"),
        'product_id': fields.many2one('product.product', 'Product',
                                      required=True),
        'default_code': fields.char('Reference', size=128),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'removal_date': fields.date('Expiry Date'),
        'package_id': fields.many2one('stock.quant.package', 'Package'),

    }

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Get default code and ean13"""
        self.default_code = self.product_id.default_code
        self.ean13 = self.product_id.ean13

    @api.onchange('lot_id')
    def onchange_lot_id(self):
        """ Get default code and ean13"""
        self.removal_date = self.lot_id.removal_date

    @api.onchange('package_id')
    def onchange_product_id(self):
        """ Get default code and ean13"""
        if self.package_id.product_id:
            self.product_id = self.package_id.product_id.id
            self.default_code = self.package_id.product_id.default_code
            self.lot_id = self.package_id.quant_ids and \
                self.package_id.quant_ids[0].lot_id and \
                self.package_id.quant_ids[0].lot_id.id
