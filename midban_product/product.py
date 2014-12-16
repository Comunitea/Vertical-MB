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
import time
from openerp.tools.translate import _
from openerp import netsvc


class temp_type(osv.Model):
    """ This model lets you spicify the deny product reason.
        You can select it in the deny product wizard when yo deny the refiste
        of a product. """
    _name = 'temp.type'
    _columns = {
        'temp_id': fields.integer('Temp id', readonly="True"),
        'name': fields.char('Temp name', size=256, required="True",
                            readonly="True"),
        'type': fields.selection([('chilled', 'Chilled'), ('frozen', 'Frozen'),
                                 ('dry', 'Dry')], "Type", help="Depending on "
                                 "this temperature, the product will be stored"
                                 "in a different warehouse location."),
    }


class unregister_product_reason(osv.Model):
    """ This model lets you spicify the unregister product reason.
        You can select it in the unregister product wizard when yo unregister a
        product. """
    _name = 'unregister.product.reason'
    _columns = {
        'name': fields.char('Unregister reason', size=256, required="True"),
    }


class deny_product_reason(osv.Model):
    """ This model lets you spicify the deny product reason.
        You can select it in the deny product wizard when yo deny the refiste
        of a product. """
    _name = 'deny.product.reason'
    _columns = {
        'name': fields.char('Unregister reason', size=256, required="True"),
    }


class product_allergen(osv.Model):
    """ Model preloaded whit 14 allergen, you can select it in product view
        in a m2m relationship.
    """
    _name = 'product.allergen'
    _columns = {
        'name': fields.char('Allergen name', size=256, required="True"),
    }


class product_template(osv.Model):
    """ Adds custom fields for midban in product view, a history of price
        and a history thats records product changes.
        Product have a unique sequence but can bee overwriten.
        It adds supplier units for purchases and mandatory units for sales"""

    def _get_last_price(self, cr, uid, ids, field_name, arg, context):
        """ Calculates the last purchase price searching in purchase order
            lines"""
        res = {}
        line_pool = self.pool.get('purchase.order.line')
        for product in self.browse(cr, uid, ids):
            res[product.id] = 0.0
            domain = [('product_id', '=', product.id)]
            purchase_line_id = line_pool.search(cr,
                                                uid,
                                                domain,
                                                limit=1,
                                                order='create_date desc')
            if purchase_line_id:

                line = line_pool.browse(cr, uid, purchase_line_id[0])
                if line.order_id.state == 'done':
                    res[product.id] = line.price_unit

        return res

    _inherit = 'product.template'
    _columns = {
        'ean14': fields.char('Code EAN14', size=14),
        'temp_type': fields.many2one('temp.type',
                                     'Temp type'),
        'sale_type': fields.selection([('fresh', 'Fresh'),
                                       ('ultrafresh', 'Ultrafresh'),
                                       ('frozen', 'Frozen'), ('dry', 'Dry')],
                                      "Sale type"),
        'var_weight': fields.boolean('Variable weight'),
        'consignment': fields.boolean('Consignment'),
        'temperature': fields.float("Temperature", digits=(8, 2)),
        'bulk': fields.boolean("Bulk"),  # granel
        'product_type': fields.selection([('food', 'Food'), ('mixed', 'Mixed'),
                                          ('hospitality', 'Hospitality')],
                                         "Product Class"),
        'mark': fields.char('Mark', size=128),
        'ref': fields.char('Referencia', size=64),
        'scientific_name': fields.char('Scientific name', size=128),
        'glazed': fields.boolean("Glazed"),
        'glazed_percent': fields.float("%", digits=(4, 2)),
        'web': fields.char('Web', size=128),
        'life': fields.integer('Useful life'),
        'first_course': fields.boolean("First Course"),
        'second_course': fields.boolean("Second Course"),
        'dessert': fields.boolean("Dessert"),
        'breakfast_snack': fields.boolean("Breakfast/Snack"),
        'accompaniment': fields.boolean("Accompaniment"),
        'product_allergen_ids': fields.many2many('product.allergen',
                                                 'product_allergen_rel',
                                                 'product_id',
                                                 'allergen_id',
                                                 'Products allergens'),

        'history_ids': fields.one2many('product.history', 'product_id',
                                       'Product History', ondelete="cascade"),
        'state2': fields.selection([
            ('val_pending', 'Validate pending'),
            ('logic_pending', 'Logistic validation pending'),
            ('commercial_pending', 'Comercial validation pending'),
            ('validated', 'Validated'),
            ('registered', 'Registered'),
            ('unregistered', 'Unegistered'),
            ('denied', 'Denied')], 'Status',
            readonly=True, required=True),
        'unregister_reason_id': fields.many2one('unregister.product.reason',
                                                'Unregister Reason',
                                                readonly=True),
        'deny_reason_id': fields.many2one('deny.product.reason',
                                          'Deny Reason',
                                          readonly=True),
        'kg_un': fields.float("KG/UN", digits=(4, 2), required=True),
        'un_ca': fields.float("UN/CA", digits=(4, 2), required=True),
        'ca_ma': fields.float("CA/MA", digits=(4, 2), required=True),
        'ma_pa': fields.float("MA/PA", digits=(4, 2), required=True),
        'un_width': fields.float("UN Width", digits=(4, 2), required=True),
        'ca_width': fields.float("CA Width", digits=(4, 2), required=True),
        'ma_width': fields.float("MA Width", digits=(4, 2), required=True),
        'pa_width': fields.float("PA Width", digits=(4, 2), required=True),
        'un_height': fields.float("UN Height", digits=(4, 2), required=True),
        'ca_height': fields.float("CA Height", digits=(4, 2), required=True),
        'ma_height': fields.float("MA Height", digits=(4, 2), required=True),
        'pa_height': fields.float("PA Height", digits=(4, 2), required=True),
        'un_length': fields.float("UN Length", digits=(4, 2), required=True),
        'ca_length': fields.float("CA Length", digits=(4, 2), required=True),
        'ma_length': fields.float("MA Length", digits=(4, 2), required=True),
        'pa_length': fields.float("PA Length", digits=(4, 2), required=True),
        'supplier_kg_un': fields.float("KG/UN Supplier", digits=(4, 2),
                                       required=True),
        'supplier_un_width': fields.float("UN Width Supplier", digits=(4, 2),
                                          required=True),
        'supplier_un_height': fields.float("UN Height Supplier", digits=(4, 2),
                                           required=True),
        'supplier_un_length': fields.float("UN Length Supplier", digits=(4, 2),
                                           required=True),
        'supplier_ca_ma': fields.float("CA/MA Supplier", digits=(4, 2),
                                       required=True),
        'supplier_ma_width': fields.float("MA Width Supplier", digits=(4, 2),
                                          required=True),
        'supplier_ma_height': fields.float("MA Height Supplier", digits=(4, 2),
                                           required=True),
        'supplier_ma_length': fields.float("MA Length Supplier", digits=(4, 2),
                                           required=True),
        'supplier_ma_pa': fields.float("MA/PA Supplier", digits=(4, 2),
                                       required=True),
        'supplier_pa_width': fields.float("PA Width Supplier", digits=(4, 2),
                                          required=True),
        'supplier_pa_height': fields.float("PA Height Supplier", digits=(4, 2),
                                           required=True),
        'supplier_pa_length': fields.float("PA Length Supplier", digits=(4, 2),
                                           required=True),
        'supplier_un_ca': fields.float("UN/CA Supplier", digits=(4, 2),
                                       required=True),
        'supplier_ca_width': fields.float("CA Width Supplier", digits=(4, 2),
                                          required=True),
        'supplier_ca_height': fields.float("CA Height Supplier", digits=(4, 2),
                                           required=True),
        'supplier_ca_length': fields.float("CA Length Supplier", digits=(4, 2),
                                           required=True),
        'palet_wood_height': fields.float("Palet Wood Height", digits=(5, 3)),
        'mantle_wood_height': fields.float("Mantle Wood Height",
                                           digits=(5, 3)),
        'last_purchase_price': fields.function(_get_last_price,
                                               string="Last purchase change",
                                               type="float",
                                               digits_compute=
                                               dp.get_precision('Account'),
                                               method=True,
                                               readonly=True),
        'margin': fields.float("Margin", digits=(4, 2)),
    }
    _defaults = {
        'default_code': lambda obj, cr, uid, context: '/',
        'state2': 'val_pending',
        'palet_wood_height': 0.145,
        'mantle_wood_height': 0.02,
        'active': False,  # Product desuctived until register state is reached
    }
    # _sql_constraints = [('ref_uniq', 'unique(default_code)',
    #                      'The reference must be unique!'), ]

    def _check_units_values(self, cr, uid, ids, context=None):
        p = self.browse(cr, uid, ids[0], context=context)
        if not (p.supplier_kg_un and p.supplier_un_width and
                p.supplier_un_height and p.supplier_un_length and
                p.supplier_ca_ma and p.supplier_ma_width and
                p.supplier_ma_height and p.supplier_ma_length and
                p.supplier_ma_pa and p.supplier_pa_width and
                p.supplier_pa_height and p.supplier_pa_length and
                p.supplier_un_ca and p.supplier_ca_width and
                p.supplier_ca_height and p.supplier_ca_length and
                p.palet_wood_height and
                p.kg_un and p.un_ca and p.ca_ma and p.ma_pa and
                p.un_width and p.ca_width and p.ma_width and p.pa_width and
                p.un_height and p.ca_height and p.ma_height and p.pa_height and
                p.un_length and p.ca_length and p.ma_length and p.pa_length):
            return False
        return True

    _constraints = [(_check_units_values, 'Error!\nSome unit dimension is \
        equals to zero. Please check it', ['supplier_kg_un',
                                           'supplier_un_width',
                                           'supplier_un_height',
                                           'supplier_un_length',
                                           'supplier_ca_ma',
                                           'supplier_ma_width',
                                           'supplier_ma_height',
                                           'supplier_ma_length',
                                           'supplier_ma_pa',
                                           'supplier_pa_width',
                                           'supplier_pa_height',
                                           'supplier_pa_length',
                                           'supplier_un_ca',
                                           'supplier_ca_width',
                                           'supplier_ca_height',
                                           'supplier_ca_length',
                                           'palet_wood_height',
                                           'kg_un',
                                           'un_ca',
                                           'ca_ma',
                                           'ma_pa',
                                           'un_width',
                                           'ca_width',
                                           'ma_width',
                                           'pa_width',
                                           'un_height',
                                           'ca_height',
                                           'ma_height',
                                           'pa_height',
                                           'un_length',
                                           'ca_length',
                                           'ma_length',
                                           'pa_length',
                                           ])]


class product(osv.Model):
    """ Adds custom fields for midban in product view, a history of price
        and a history thats records product changes.
        Product have a unique sequence but can bee overwriten.
        It adds supplier units for purchases and mandatory units for sales"""

    _inherit = 'product.product'
    _defaults = {
        'active': False,  # Product desuctived until register state is reached
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """ Overwrites copy methos in order to no duplicate the history,
        the price history, and the sequence"""
        default = {} if default is None else default.copy()
        default.update({
            'history_ids': [],
            'unregister_reason_id': False,
            'deny_reason_id': False,
            'default_code': '/'
        })
        return super(product, self).copy(cr, uid, id, default=default,
                                         context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        if 'consignment' in vals:
            raise osv.except_osv(_('Warning!'),
                                 _('You cannot change the value \
                                    of consignment field.'))
        return super(product, self).write(cr, uid, ids,
                                          vals, context=context)

    def create(self, cr, user, vals, context=None):
        """ Generates a sequence in the internal reference name.
            This sequence must be unique by product. And can be changed
            by user."""
        if ('default_code' not in vals) or (vals.get('default_code') == '/'):
            sequence_obj = self.pool.get('ir.sequence')
            vals['default_code'] = sequence_obj.get(cr, user,
                                                    'product.serial.number')
        new_id = super(product, self).create(cr, user, vals, context)
        return new_id

    def _update_history(self, cr, uid, ids, context, product_obj, activity):
        """ Update product history model for the argument partner_obj whith
            the activity defined in activity argument."""
        vals = {
            'product_id': product_obj.id,
            'user_id': uid,
            'date': time.strftime("%Y-%m-%d %H:%M:%S"),
            'activity': activity
        }
        self.pool.get("product.history").create(cr, uid, vals, context)
        return True

    def act_validate_pending(self, cr, uid, ids, context=None):
        """ Fix state in validate pending, product no active, update history.
            It's a flow method."""
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            product.write({'state2': 'val_pending', 'active': False})
            message = _("Pending logistic and commercial validate")
            self._update_history(cr, uid, ids, context, product, message)
        return True

    def act_comercial_pending(self, cr, uid, ids, context=None):
        """ Fix state in commercial pending, product no active,
            update history. It's a flow method."""
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            message = _("Logistic validate done")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'commercial_pending', 'active': False})
        return True

    def act_logic_pending(self, cr, uid, ids, context=None):
        """ Fix state in logic pending, product no active,
            update history. It's a flow method."""
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            message = _("Comercial validate done")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'logic_pending', 'active': False})
        return True

    def act_validated(self, cr, uid, ids, context=None):
        """ Fix state in validated, product no active,
            update history. It's a flow method."""
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            message = _("Comercial and validate done. Pending to register")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'validated', 'active': False})
        return True

    def act_active(self, cr, uid, ids, context=None):
        """ Fix state in registered, product active,
            update history. It's a flow method."""
        t_template = self.pool.get("product.template")
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            message = _("Product registered")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'registered', 'active': True,
                           'sale_ok': True, 'purchase_ok': True})
            template = t_template.browse(cr, uid, product.product_tmpl_id.id,
                                         context)
            template.write({'active': True})
        return True

    def act_denied(self, cr, uid, ids, context=None):
        """ Button deny method. that set register state again afeter a product
            was unregistered."""
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            message = _("Product denyed")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'denied', 'active': False,
                           'sale_ok': True, 'purchase_ok': True})
        return True

    def register_again(self, cr, uid, ids, context=None):
        """ Fix state in registered when a product was unregistered,
            product active, update history. It's a button method."""
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            message = _("Product registered again")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'registered', 'active': True,
                           'sale_ok': True, 'purchase_ok': True})
        return True

    def flow_restart(self, cr, uid, ids, context=None):
        """ When a product is denied this method lets you restart the product
            workflow so the product will be desactived and state its fixed to
            validate pending."""
        for product in self.pool.get("product.product").browse(cr, uid, ids):
            message = _("Product denied in register process again")
            self._update_history(cr, uid, ids, context, product, message)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_delete(uid, 'product.product', product.id, cr)
            wf_service.trg_create(uid, 'product.product', product.id, cr)
        return True


class product_history(osv.Model):
    """ Every time a status change is reached it will be registered in this
    model."""
    _name = 'product.history'
    _description = "Product history"
    _rec_name = "product_id"
    _order = "date desc"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product',
                                      readonly=True, required=True, ),
        'user_id': fields.many2one("res.users", 'User', readonly=True,
                                   required=True),
        'date': fields.datetime('Date', readonly=True, required=True),
        'activity': fields.char('Activity', size=256),
        'reason': fields.char('Reason', size=256),
        'comment': fields.text('Comment')
    }
