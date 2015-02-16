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
        t_picking = self.pool.get('stock.picking')
        if context.get('active_model', False) and \
                context.get('active_id', False)and \
                context['active_model'] == 'stock.picking':
            active_id = context['active_id']
            picking_obj = t_picking.browse(cr, uid, active_id, context=context)
            for op in picking_obj.pack_operation_ids:
                if op.pack_type == 'palet':
                    vals = {}
                    prod = op.operation_product_id and \
                        op.operation_product_id or False
                    purchase_id = picking_obj.purchase_id and \
                        picking_obj.purchase_id.id or False
                    num_units = 0
                    num_boxes = 0
                    vals = {
                        'product_id': prod.id,
                        'default_code': prod.default_code,
                        'ean13': prod.ean13,
                        'purchase_id': purchase_id,
                        'type': 'palet',
                        'lot_id': op.lot_id and op.lot_id.id or False,
                        'removal_date': op.lot_id and
                                op.lot_id.removal_date or False
                    }
                    if prod and picking_obj.picking_type_code == 'incoming':
                        num_units = op.product_qty
                    elif prod and picking_obj.picking_type_code == 'internal':
                        num_units = op.package_id.packed_qty - op.product_qty
                        vals['lot_id'] = op.package_id and \
                            (op.package_id.packed_lot_id and
                             op.package_id.packed_lot_id.id or False) or False
                    if vals:
                        num_boxes = prod.un_ca and \
                            num_units / prod.un_ca or 0
                        vals['num_units'] = num_units
                        vals['num_boxes'] = num_boxes
                        vals['weight'] = num_units * prod.kg_un
                        item_ids.append(t_item.create(cr, uid, vals, context))
        res.update({'tag_ids': item_ids})
        if context.get('show_print_report', False):
            res.update({'show_print_report': True})
        return res

    _columns = {
        'tag_ids': fields.one2many('tag.item', 'wizard_id', 'Tags'),
        'show_print_report': fields.boolean('Show', readonly=True),
        'printed': fields.boolean('Printed', readonly=True),
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
                'default_code': item.default_code,
                'ean13': item.ean13,
                'purchase_id': item.purchase_id and item.purchase_id.id
                or False,
                'type': item.type,
                'weight': item.weight,
                'num_units': item.num_units,
                'num_boxes': item.num_boxes,
                'lot_id': item.lot_id and item.lot_id.id or False,
                'removal_date': item.removal_date
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

        if context.get('active_model', False) == 'stock.picking':
            picking_id = context.get('active_id', False)
            if picking_id:
                ctx['active_ids'] = [picking_id]
                ctx['active_model'] = 'stock.picking'
            return self.pool.get("report").\
                get_action(cr, uid, [],
                           'midban_depot_stock.report_picking_task',
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
        'ean13': fields.char('EAN13', size=13),
        'purchase_id': fields.many2one('purchase.order', 'Purchase order'),
        'type': fields.selection([('box', 'Box'), ('palet', 'Palet')],
                                 string="Type", required=True),
        'num_units': fields.float('Units'),
        'num_boxes': fields.float('Boxes'),
        'weight': fields.float('Weight'),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'removal_date': fields.date('Expiry Date')

    }

    _defauls = {
        'type': 'palet',
    }

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Get default code and ean13"""
        self.default_code = self.product_id.default_code
        self.ean13 = self.product_id.ean13
        self.weight = self.product_id.kg_un
        self.units = 1

    @api.onchange('lot_id')
    def onchange_lot_id(self):
        """ Get default code and ean13"""
        self.removal_date = self.lot_id.removal_date

    @api.onchange('num_units')
    def onchange_units(self):
        """ Get boxes and new weight"""
        if self.product_id and self.product_id.un_ca:
            self.num_boxes = self.num_units / self.product_id.un_ca
            self.weight = self.product_id.kg_un * self.num_units

    @api.onchange('num_boxes')
    def onchange_boxes(self):
        """ Get units and new weight"""
        if self.product_id and self.product_id.un_ca:
            self.num_units = self.num_boxes * self.product_id.un_ca
            self.weight = self.product_id.kg_un * self.num_units
