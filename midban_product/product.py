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
from openerp import models, api
from openerp import fields as fields2
from openerp.exceptions import except_orm
from openerp.tools.float_utils import float_round
import operator
import functools



class temp_type(osv.Model):
    """ This model lets you spicify the deny product reason.
        You can select it in the deny product wizard when yo deny the refiste
        of a product. """
    _name = 'temp.type'
    _columns = {
        'temp_id': fields.integer('Temp id', readonly="True"),
        'name': fields.char('Temp name', size=256, required="True"),
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

    def _get_hidde_variant_page(self, cr, uid, ids, field_name, arg, context):
        res = {}
        dummy, group_id = self.pool.get('ir.model.data').get_object_reference(
            cr, 1, 'midban_product', 'group_no_variants')
        user = self.pool.get('res.users').browse(cr, uid, uid)
        for product in self.browse(cr, uid, ids):
            if group_id in [x.id for x in user.groups_id]:
                res[product.id] = False
            else:
                res[product.id] = True
        return res

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
                                     'Temp type', help="Informative field that"
                                     "should be the same as the picking"
                                     "location temperature type"),
        'var_weight': fields.boolean('Variable weight'),
        'consignment': fields.boolean('Consignment'),
        'temperature': fields.float("Temperature", digits=(8, 2)),
        'bulk': fields.boolean("Bulk"),  # granel
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

        'history_ids': fields.one2many('product.history', 'product_tmp_id',
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
        'kg_un': fields.float("KG/UN", digits=(4, 2)),
        'un_ca': fields.float("UN/CA", digits=(4, 2)),
        'ca_ma': fields.float("CA/MA", digits=(4, 2)),
        'ma_pa': fields.float("MA/PA", digits=(4, 2)),
        'un_width': fields.float("UN Width", digits=(4, 2)),
        'ca_width': fields.float("CA Width", digits=(4, 2)),
        'ma_width': fields.float("MA Width", digits=(4, 2)),
        'pa_width': fields.float("PA Width", digits=(4, 2)),
        'un_height': fields.float("UN Height", digits=(4, 2)),
        'ca_height': fields.float("CA Height", digits=(4, 2)),
        'ma_height': fields.float("MA Height", digits=(4, 2)),
        'pa_height': fields.float("PA Height", digits=(4, 2)),
        'un_length': fields.float("UN Length", digits=(4, 2)),
        'ca_length': fields.float("CA Length", digits=(4, 2)),
        'ma_length': fields.float("MA Length", digits=(4, 2)),
        'pa_length': fields.float("PA Length", digits=(4, 2)),
        'supplier_kg_un': fields.float("KG/UN Supplier", digits=(4, 2)),
        'supplier_un_width': fields.float("UN Width Supplier",
                                          digits=(4, 2)),
        'supplier_un_height': fields.float("UN Height Supplier",
                                           digits=(4, 2)),
        'supplier_un_length': fields.float("UN Length Supplier",
                                           digits=(4, 2)),
        'supplier_ca_ma': fields.float("CA/MA Supplier", digits=(4, 2)),
        'supplier_ma_width': fields.float("MA Width Supplier",
                                          digits=(4, 2)),
        'supplier_ma_height': fields.float("MA Height Supplier",
                                           digits=(4, 2)),
        'supplier_ma_length': fields.float("MA Length Supplier",
                                           digits=(4, 2)),
        'supplier_ma_pa': fields.float("MA/PA Supplier",
                                       digits=(4, 2)),
        'supplier_pa_width': fields.float("PA Width Supplier",
                                          digits=(4, 2)),
        'supplier_pa_height': fields.float("PA Height Supplier",
                                           digits=(4, 2)),
        'supplier_pa_length': fields.float("PA Length Supplier",
                                           digits=(4, 2)),
        'supplier_un_ca': fields.float("UN/CA Supplier",
                                       digits=(4, 2)),
        'supplier_ca_width': fields.float("CA Width Supplier",
                                          digits=(4, 2)),
        'supplier_ca_height': fields.float("CA Height Supplier",
                                           digits=(4, 2)),
        'supplier_ca_length': fields.float("CA Length Supplier",
                                           digits=(4, 2)),
        'palet_wood_height': fields.float("Palet Wood Height", digits=(5, 3),
                                          help='Size wood pallet, affects the \
calculation of the volume'),
        'last_purchase_price': fields.function(_get_last_price,
                                               string="Last purchase change",
                                               type="float",
                                               digits_compute=
                                               dp.get_precision('Account'),
                                               method=True,
                                               readonly=True),
        'margin': fields.float("Margin", digits=(4, 2),
                               help="Margin over sale order that will be used\
                                     like base to calculate the sale \
                                     pricelist of ultrafresh products"),
        # In order to put into domains and make comprobations or identify for
        # telesale and ultrafresh_module.
        'product_class': fields.selection([('normal', 'Normal'),
                                           ('fresh', 'Fresh'),
                                           ('ultrafresh', 'Ultrafresh')],
                                          'Class',
                                          required=True,
                                          help='Fresh and ultra-fresh \
products do not require units for validation'),
        'drained_weight': fields.float('Drained net weight',
                                       digits_compute=dp.get_precision
                                       ('Stock Weight')),
        'hidde_variant_page': fields.function(_get_hidde_variant_page,
                                              string="Hidde variant page",
                                              type="boolean",
                                              method=True,
                                              readonly=True)
    }
    _defaults = {
        'default_code': lambda obj, cr, uid, context: '/',
        'state2': 'val_pending',
        'palet_wood_height': 0.145,
        'active': False,  # Product desuctived until register state is reached
        'product_class': 'normal',
        'supplier_pa_width': 0.8,
        'supplier_pa_length': 1.2,
        'pa_width': 0.8,
        'pa_length': 1.2,
        'supplier_ma_length': 1.2,
        'supplier_un_ca': 1.0,

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
        return super(product_template, self).copy(cr, uid, id, default=default,
                                                  context=context)

    '''def write(self, cr, uid, ids, vals, context=None):
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
        return super(product_template, self).write(cr, uid, ids,
                                                   vals, context=context)'''

    def create(self, cr, user, vals, context=None):
        """ Generates a sequence in the internal reference name.
            This sequence must be unique by product. And can be changed
            by user."""
        if ('default_code' not in vals) or (vals.get('default_code') == '/'):
            sequence_obj = self.pool.get('ir.sequence')
            vals['default_code'] = sequence_obj.get(cr, user,
                                                    'product.serial.number')
        new_id = super(product_template, self).create(cr, user, vals, context)
        return new_id

    def _update_history(self, cr, uid, ids, context, product_obj, activity,
                        reason=False):
        """ Update product history model for the argument partner_obj whith
            the activity defined in activity argument."""
        vals = {
            'product_tmp_id': product_obj.id,
            'user_id': uid,
            'date': time.strftime("%Y-%m-%d %H:%M:%S"),
            'activity': activity,
            'reason': reason
        }
        self.pool.get("product.history").create(cr, uid, vals, context)
        return True

    def act_validate_pending(self, cr, uid, ids, context=None):
        """ Fix state in validate pending, product no active, update history.
            It's a flow method."""
        for product in self.browse(cr, uid, ids):
            product.write({'state2': 'val_pending', 'active': False})
            message = _("Pending logistic and commercial validate")
            self._update_history(cr, uid, ids, context, product, message)
        return True

    def _check_units_values(self, cr, uid, ids, context=None):
        res = True
        p = self.browse(cr, uid, ids[0], context=context)
        if p.product_class not in ['fresh', 'ultrafresh'] \
            and not p.is_cross_dock and p.type == "product" and \
            not (p.supplier_kg_un and p.supplier_un_width and
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
                 p.un_height and p.ca_height and p.ma_height and p.pa_height
                 and p.un_length and p.ca_length and p.ma_length
                 and p.pa_length):
            res = False
        if not res:
            raise osv.except_osv(_('Error'), _('Some unit dimension is equals \
                                               to zero. Please check it'))
        return res

    def act_comercial_pending(self, cr, uid, ids, context=None):
        """ Fix state in commercial pending, product no active,
            update history. It's a flow method."""
        for product in self.browse(cr, uid, ids):
            product._check_units_values()
            message = _("Logistic validate done")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'commercial_pending', 'active': False})
        return True

    def act_logic_pending(self, cr, uid, ids, context=None):
        """ Fix state in logic pending, product no active,
            update history. It's a flow method."""
        for product in self.browse(cr, uid, ids):

            message = _("Comercial validate done")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'logic_pending', 'active': False})
        return True

    def act_validated(self, cr, uid, ids, context=None):
        """ Fix state in validated, product no active,
            update history. It's a flow method."""
        for product in self.browse(cr, uid, ids):
            product._check_units_values()
            message = _("Comercial and validate done. Pending to register")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'validated', 'active': False})
        return True

    def act_active(self, cr, uid, ids, context=None):
        """ Fix state in registered, product active,
            update history. It's a flow method."""
        t_template = self.pool.get("product.template")
        for product in self.browse(cr, uid, ids):
            message = _("Product registered")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'registered', 'active': True,
                           'sale_ok': True, 'purchase_ok': True})
            template = t_template.browse(cr, uid, product.id,
                                         context)
            template.write({'active': True})
        return True

    def act_denied(self, cr, uid, ids, context=None):
        """ Button deny method. that set register state again afeter a product
            was unregistered."""
        for product in self.browse(cr, uid, ids):
            message = _("Product denyed")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'denied', 'active': False,
                           'sale_ok': True, 'purchase_ok': True})
        return True

    def register_again(self, cr, uid, ids, context=None):
        """ Fix state in registered when a product was unregistered,
            product active, update history. It's a button method."""
        for product in self.browse(cr, uid, ids):
            message = _("Product registered again")
            self._update_history(cr, uid, ids, context, product, message)
            product.write({'state2': 'registered', 'active': True,
                           'sale_ok': True, 'purchase_ok': True})
        return True

    def flow_restart(self, cr, uid, ids, context=None):
        """ When a product is denied this method lets you restart the product
            workflow so the product will be desactived and state its fixed to
            validate pending."""
        for product in self.browse(cr, uid, ids):
            message = _("Product denied in register process again")
            self._update_history(cr, uid, ids, context, product, message)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_delete(uid, 'product.template', product.id, cr)
            wf_service.trg_create(uid, 'product.template', product.id, cr)
        return True


class product_history(osv.Model):
    """ Every time a status change is reached it will be registered in this
    model."""
    _name = 'product.history'
    _description = "Product history"
    _rec_name = "product_tmp_id"
    _order = "date desc"
    _columns = {
        'product_tmp_id': fields.many2one('product.template', 'Product',
                                          readonly=True, required=True,
                                          ondelete="cascade"),
        'user_id': fields.many2one("res.users", 'User', readonly=True,
                                   required=True),
        'date': fields.datetime('Date', readonly=True, required=True),
        'activity': fields.char('Activity', size=256),
        'reason': fields.char('Reason', size=256),
        'comment': fields.text('Comment')
    }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_kg_unit(self):
        return self.env.ref('product.product_uom_kgm').id

    var_coeff_un = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units')
    var_coeff_ca = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units.')
    log_base_id = fields2.Many2one('product.uom', 'Base',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic base',
                                   default=_get_kg_unit)
    log_box_id = fields2.Many2one('product.uom', 'Box',
                                  help='The defined unit of measure will be'
                                  ' related with the logistic box')
    log_unit_id = fields2.Many2one('product.uom', 'Unit',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic unit')

    base_use_sale = fields2.Boolean('Can be used on sales',
                                    help='Allows you to sale in the defined'
                                    ' logistic base.')
    unit_use_sale = fields2.Boolean('Can be used on sales',
                                    help='Allows you to sale in the defined'
                                    ' logistic unit.')
    box_use_sale = fields2.Boolean('Can be used on sales',
                                   help='Allows you to sale in the defined'
                                   ' logistic box')
    is_var_coeff = fields2.Boolean("Variable weight", readonly=True,
                                   compute='_get_is_var_coeff',
                                   store=True,
                                   help="If any conversion is checked, the \
                                   product will be processed as a variable \
                                   weight product in sales process")

    @api.model
    @api.depends('var_coeff_un', 'var_coeff_ca')
    def _get_is_var_coeff(self):
        """
        Calc name str
        """
        self.is_var_coeff = self.var_coeff_un or self.var_coeff_ca


class product_product(models.Model):

    _inherit = "product.product"

    @api.model
    def get_sale_unit_ids(self):
        res = []
        if self.base_use_sale and self.log_base_id:
            res.append(self.log_base_id.id)
        if self.unit_use_sale and self.log_unit_id:
            res.append(self.log_unit_id.id)
        if self.box_use_sale and self.log_box_id:
            res.append(self.log_box_id.id)
        return res

    @api.model
    def _get_factor(self, uos_id):
        uom_id = self.uom_id.id
        if uos_id == self.log_base_id.id:
            if uom_id == self.log_base_id.id:
                return 1
            if uom_id == self.log_unit_id.id:
                return 1/self.kg_un
            if uom_id == self.log_box_id.id:
                return 1 / (self.kg_un * self.un_ca)

        if uos_id == self.log_unit_id.id:
            if uom_id == self.log_base_id.id:
                return self.kg_un
            if uom_id == self.log_unit_id.id:
                return 1
            if uom_id == self.log_box_id.id:
                return 1 / self.un_ca * self.un_ca

        if uos_id == self.log_box_id.id:
            if uom_id == self.log_base_id.id:
                return self.kg_un * self.un_ca
            if uom_id == self.log_unit_id.id:
                return self.un_ca
            if uom_id == self.log_box_id.id:
                return 1
        raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_id.name))

    @api.model
    def uom_qty_to_uos_qty(self, uom_qty, uos_id):
        return uom_qty / self._get_factor(uos_id)

    @api.model
    def uos_qty_to_uom_qty(self, uos_qty, uos_id):
        return self._get_factor(uos_id) * uos_qty

    @api.model
    def get_uom_logistic_unit(self):
        if self.uom_id.id == self.log_base_id.id:
            return 'base'
        elif self.uom_id.id == self.log_unit_id.id:
            return 'unit'
        elif self.uom_id.id == self.log_box_id.id:
            return 'box'
        else:
            raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_id.name))

    def get_uos_logistic_unit(self, uos_id):
        if uos_id == self.log_base_id.id:
            return 'base'
        elif uos_id == self.log_unit_id.id:
            return 'unit'
        elif uos_id == self.log_box_id.id:
            return 'box'
        else:
            raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_id.name))

    @api.model
    def get_uom_uos_prices(self, uos_id, custom_price_unit=0.0,
                           custom_price_udv=0.0):
        if custom_price_udv:
            price_udv = custom_price_udv
            price_unit = price_udv / self._get_factor(uos_id)
        else:
            price_unit = custom_price_unit or self.lst_price
            price_udv = price_unit * self._get_factor(uos_id)
        return price_unit, price_udv

    @api.multi
    def get_palet_size(self, from_unit):
        """

        :param from_unit: Unidad desde la que se convertira a palet
        """
        self.ensure_one()
        conversion_fields = ['ca_ma', 'ma_pa']
        conversions = {
            self.log_base_id.id: ['kg_un', 'un_ca'],
            self.log_unit_id.id: ['un_ca'],
            self.log_box_id.id: [],

        }
        conversion_fields += conversions[from_unit.id]
        return functools.reduce(operator.mul, [self[x] for x in conversion_fields])



class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    def _get_kg_unit(self):
        return self.env.ref('product.product_uom_kgm').id

    var_coeff_un = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units')
    var_coeff_ca = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units.')
    log_base_id = fields2.Many2one('product.uom', 'Base',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic base',
                                   default=_get_kg_unit)
    log_box_id = fields2.Many2one('product.uom', 'Box',
                                  help='The defined unit of measure will be'
                                  ' related with the logistic unit')
    log_unit_id = fields2.Many2one('product.uom', 'Unit',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic box')

    base_use_purchase = fields2.Boolean('Can be used on purchases',
                                        help='Allows you to buy in the defined'
                                        ' logistic base.')
    unit_use_purchase = fields2.Boolean('Can be used on purchases',
                                        help='Allows you to buy in the defined'
                                        ' logistic unit.')
    box_use_purchase = fields2.Boolean('Can be used on purchases',
                                       help='Allows you to buy in the defined'
                                       ' logistic box')
    supp_kg_un = fields2.Float("KG/UN Supplier", digits=(4, 2))
    supp_un_width = fields2.Float("UN Width Supplier", digits=(4, 2))
    supp_un_height = fields2.Float("UN Height Supplier", digits=(4, 2))
    supp_un_length = fields2.Float("UN Length Supplier", digits=(4, 2))
    supp_ca_ma = fields2.Float("CA/MA Supplier", digits=(4, 2))
    supp_ma_width = fields2.Float("MA Width Supplier", digits=(4, 2))
    supp_ma_height = fields2.Float("MA Height Supplier", digits=(4, 2))
    supp_ma_length = fields2.Float("MA Length Supplier", digits=(4, 2))
    supp_ma_pa = fields2.Float("MA/PA Supplier", digits=(4, 2))
    supp_pa_width = fields2.Float("PA Width Supplier", digits=(4, 2))
    supp_pa_height = fields2.Float("PA Height Supplier", digits=(4, 2))
    supp_pa_length = fields2.Float("PA Length Supplier", digits=(4, 2))
    supp_un_ca = fields2.Float("UN/CA Supplier", digits=(4, 2))
    supp_ca_width = fields2.Float("CA Width Supplier", digits=(4, 2))
    supp_ca_height = fields2.Float("CA Height Supplier", digits=(4, 2))
    supp_ca_length = fields2.Float("CA Length Supplier", digits=(4, 2))

    is_var_coeff = fields2.Boolean("Variable weight", readonly=True,
                                   compute='_get_is_var_coeff',
                                   store=True,
                                   help="If any conversion is checked, the \
                                   product will be processed as a variable \
                                   weight product in purchases process")

    @api.multi
    @api.depends('var_coeff_un', 'var_coeff_ca')
    def _get_is_var_coeff(self):
        """
        Calc name str
        """
        for supp_prod in self:
            supp_prod.is_var_coeff = supp_prod.var_coeff_un or \
                supp_prod.var_coeff_ca
