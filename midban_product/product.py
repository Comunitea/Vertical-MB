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
import operator
import functools
from openerp.tools.float_utils import float_round
import math


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
        'ean_consum': fields.char('EAN Consum', size=14),
        'temp_type': fields.many2one('temp.type',
                                     'Temp type', help="Informative field that"
                                     "should be the same as the picking"
                                     "location temperature type",
                                     required=True),
        'consignment': fields.boolean('Consignment'),
        'temperature': fields.float("Temperature", digits=(8, 2)),
        'bulk': fields.boolean("Bulk"),  # granel
        'mark': fields.char('Mark', size=128),
        'ref': fields.char('Referencia', size=64),
        'scientific_name': fields.char('Scientific name', size=128),
        'glazed': fields.boolean("Glazed"),
        'no_gluten': fields.boolean("No Gluten"),
        'glazed_percent': fields.float("%", digits=(4, 2)),
        'web': fields.char('Web', size=128),
        # 'life': fields.integer('Useful life'),
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
                                              readonly=True),
        'doorstep_price': fields.float("Doorstep Price", digits=(4, 2)),
        'nook_price': fields.float('Nook Price', digits=(4, 2))
    }
    _defaults = {
        'default_code': lambda obj, cr, uid, context: '/',
        'state2': 'val_pending',
        'palet_wood_height': 0.145,
        'active': False,  # Product desuctived until register state is reached
        'product_class': 'normal',
        'pa_width': 0.8,
        'pa_length': 1.2,
        'kg_un': 1.0,
        'un_ca': 1.0,
        'ca_ma': 1.0,
        'ma_pa': 1.0,
        'type': 'product'
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

    def action_copy_logistic_info (self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]

        for product in self.browse(cr, uid, ids, context=context):
            vals = {
                'supp_kg_un':product.kg_un,
                'supp_un_ca':product.un_ca,
                'supp_ca_ma':product.ca_ma,
                'supp_ma_pa':product.ma_pa,
                'supp_un_width':product.un_width,
                'supp_ca_width':product.ca_width,
                'supp_ma_width':product.ma_width,
                'supp_pa_width':product.pa_width,
                'supp_un_height':product.un_height,
                'supp_ca_height':product.ca_height,
                'supp_ma_height':product.ma_height,
                'supp_pa_height':product.pa_height,
                'supp_un_length':product.un_length,
                'supp_ca_length':product.ca_length,
                'supp_ma_length':product.ma_length,
                'supp_pa_length':product.pa_length,

                # 'var_coeff_un':product.var_coeff_un,
                # 'var_coeff_ca':product.var_coeff_ca,
                # 'log_base_id':product.log_base_id and product.log_base_id.id or False,
                # 'log_unit_id':product.log_unit_id and product.log_unit_id.id or False,
                # 'log_box_id':product.log_box_id and product.log_box_id.id or False,
                # 'base_use_purchase':product.base_use_sale,
                # 'unit_use_purchase':product.unit_use_sale,
                # 'box_use_purchase':product.box_use_sale,
                # 'is_var_coeff':product.is_var_coeff,
            }
            supp_info_ids = [x.id for x in product.seller_ids]
            self.pool.get('product.supplierinfo').write(cr, uid, supp_info_ids, vals, context=context)

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

    def write(self, cr, uid, ids, vals, context=None):
        ''' We don't need to no control change of uom if not validated product'''
        if isinstance(ids, (int, long)):
            ids = [ids]

        validated_ids = []
        not_validated_ids = []
        for product in self.browse(cr, uid, ids, context=context):
            if product.state2 not in ['validated',
                                   'registered',
                                   'unregistered',
                                   'denied'] and \
                            'uom_po_id' in vals:
                not_validated_ids.append(product.id)
            else:
                validated_ids.append(product.id)

        if not_validated_ids:
            uom_vals = {}
            if vals.get('uom_id'):
                uom_vals['uom_id'] = vals.pop('uom_id')
            if vals.get('uom_id'):
                uom_vals['uom_po_id'] = vals.pop('uom_po_id')
            res = super(product_template, self).write(cr, uid, not_validated_ids, vals, context)
            osv.osv.write(self, cr, uid, not_validated_ids, uom_vals, context=context)
        if  validated_ids:
            return super(product_template, self).write(cr, uid, validated_ids, vals, context)
        return res


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
        p = self.browse(cr, uid, ids[0], context=context)
        for s in p.seller_ids:
            if p.product_class not in ['fresh', 'ultrafresh'] \
                and not p.is_cross_dock and p.type == "product" and \
                not (s.supp_kg_un and s.supp_un_ca and s.supp_ca_ma and
                     s.supp_ma_pa and s.supp_pa_width and s.supp_ma_height
                     and s.supp_pa_length):
                raise osv.except_osv(_('Error'),
                                     _('Some unit dimension is '
                                       'equals to zero. Please '
                                       'check it in supplier %s') %
                                     (s.name.name))
        if p.product_class not in ['fresh', 'ultrafresh'] \
                and not p.is_cross_dock and p.type == "product" and \
                not (p.kg_un and p.un_ca and p.ca_ma and p.ma_pa and
                     p.pa_width and p.ma_height and p.pa_length):
            raise osv.except_osv(_('Error'),
                                 _('Some unit dimension is '
                                   'equals to zero. Please '
                                   'check it.'))
        if not p.weight:
            raise osv.except_osv(_('Error'),
                                 _('You need to set gross weight'))
        return True

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

    @api.model
    def _get_box_unit(self):
        return self.env.ref('midban_product.product_uom_box').id

    @api.model
    def _get_unit_unit(self):
        return self.env.ref('product.product_uom_unit').id

    var_coeff_un = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units')
    var_coeff_ca = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units.')
    log_base_id = fields2.Many2one('product.uom', 'Logistic Base',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic base',
                                   default=_get_kg_unit)
    log_box_id = fields2.Many2one('product.uom', 'Logistic Box',
                                  help='The defined unit of measure will be'
                                  ' related with the logistic box',
                                  default=_get_box_unit)
    log_unit_id = fields2.Many2one('product.uom', 'Logistic Unit',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic unit',
                                   default=_get_unit_unit)

    base_use_sale = fields2.Boolean('Can be used on sales',
                                    help='Allows you to sale in the defined'
                                    ' logistic base.')
    unit_use_sale = fields2.Boolean('Can be used on sales',
                                    help='Allows you to sale in the defined'
                                    ' logistic unit.', default=True)
    box_use_sale = fields2.Boolean('Can be used on sales',
                                   help='Allows you to sale in the defined'
                                   ' logistic box')
    is_var_coeff = fields2.Boolean("Variable weight", readonly=True,
                                   compute='_get_is_var_coeff',
                                   store=True,
                                   help="If any conversion is checked, the \
                                   product will be processed as a variable \
                                   weight product in sales process")

    @api.one
    @api.constrains('base_use_sale', 'unit_use_sale', 'box_use_sale')
    def check_use_sale_checked(self):
        if not (self.base_use_sale or self.unit_use_sale or self.box_use_sale):
            raise Warning(_('Need a logistic unit in sales'))

    @api.one
    @api.constrains('log_base_id', 'log_unit_id', 'log_box_id', 'uom_id', ' uos_id')
    def check_supplier_uoms(self):

        product_uom = self.uom_id
        if not ((product_uom == self.log_base_id) or \
                (product_uom == self.log_unit_id) or (product_uom == self.log_box_id)):
            raise Warning(_('Product uom not in logistic units \
                             ' % product_uom))

        if self.uos_id:
            product_uom = self.uos_id
            if not((product_uom == self.log_base_id) or \
                    (product_uom == self.log_unit_id) or \
                    (product_uom == self.log_box_id)):
                raise Warning(_('Product uos not in logistic units \
                                 ' % product_uom))

        unit_error = False
        if self.log_base_id:
            if (self.log_base_id == self.log_unit_id) or \
               (self.log_base_id == self.log_box_id):
                unit_error = True
        if self.log_unit_id:
            if (self.log_unit_id == self.log_base_id) or \
               (self.log_unit_id == self.log_box_id):
                unit_error = True
        if self.log_box_id:
            if (self.log_box_id == self.log_base_id) or \
               (self.log_box_id == self.log_unit_id):
                unit_error = True

        if unit_error:
            raise Warning(_('Product logistic units are wrong'))

    @api.one
    @api.depends('var_coeff_un', 'var_coeff_ca')
    def _get_is_var_coeff(self):
        """
        Calc name str
        """
        self.is_var_coeff = self.var_coeff_un or self.var_coeff_ca


class product_product(models.Model):

    _inherit = "product.product"


    #Saca la los ids de las unidades disponibles para venta
    @api.multi
    def get_sale_unit_ids(self):
        res = []
        if self.base_use_sale and self.log_base_id:
            res.append(self.log_base_id.id)
        if self.unit_use_sale and self.log_unit_id:
            res.append(self.log_unit_id.id)
        if self.box_use_sale and self.log_box_id:
            res.append(self.log_box_id.id)
        return res

    # y para compras ....
    @api.multi
    def get_purchase_unit_ids(self, supplier_id):
        res = []
        supp = self.get_product_supp_record(supplier_id)

        res = []

        if supp.base_use_purchase and supp.log_base_id:
            res.append(supp.log_base_id.id)
        if supp.unit_use_purchase and supp.log_unit_id:
            res.append(supp.log_unit_id.id)
        if supp.box_use_purchase and supp.log_box_id:
            res.append(supp.log_box_id.id)
        return res

    @api.multi
    def uom_qty_to_uos_qty(self, uom_qty, uos_id, supplier_id=0):
        round = self.env['product.uom'].browse(uos_id).rounding
        if uos_id == self.uom_id.id:
            return float_round(uom_qty,
                           precision_rounding=round
                           )
        return float_round(uom_qty * self._get_factor(uos_id, supplier_id),
                           precision_rounding=round
                           )

    @api.multi
    def uos_qty_to_uom_qty(self, uos_qty, uos_id, supplier_id=0):
        round = self.uom_id.rounding
        if uos_id == self.uom_id.id:
            return float_round(uos_qty,
                           precision_rounding=round
                           )
        return float_round(uos_qty / self._get_factor(uos_id, supplier_id),
                           precision_rounding=round
                           )


    @api.multi
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

    @api.multi
    def get_uom_uos_prices(self, uos_id, custom_price_unit=0.0,
                           custom_price_udv=0.0):
        if custom_price_udv:
            price_udv = custom_price_udv
            price_unit = price_udv * self._get_factor(uos_id)
        else:
            price_unit = custom_price_unit or self.lst_price
            price_udv = price_unit / self._get_factor(uos_id)
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
        return functools.reduce(operator.mul,
                                [self[x] for x in conversion_fields])

    @api.multi
    def get_product_supp_record(self, supplier_id):
        res = False
        for supp in self.seller_ids:
            if supp.name.id == supplier_id:
                res = supp
        if not res:
            supp_obj = self.env['res.partner'].browse(supplier_id)
            raise except_orm(_('Error'), _('Supplier %s not defined in product\
                                            supplier list') % supp_obj.name)
        return res

    @api.multi
    def uom_qty_to_uoc_qty(self, uom_qty, uoc_id, supplier_id = 0):
        """
        Convert product quantity from his default stock unit to the specified
        uoc_id, consulting the conversions in the supplier model.
        """
        supp = self.get_product_supp_record(supplier_id)
        conv = self.get_purchase_unit_conversions(uom_qty, self.uom_id.id,
                                                  supplier_id)
        if uoc_id == supp.log_base_id.id:
            return conv['base']
        elif uoc_id == supp.log_unit_id.id:
            return conv['unit']
        elif uoc_id == supp.log_box_id.id:
            return conv['box']

    @api.multi
    def get_uom_po_logistic_unit(self, supplier_id):
        supp = self.get_product_supp_record(supplier_id)
        if self.uom_id.id == supp.log_base_id.id:
            return 'base', supp.log_base_id.id
        elif self.uom_id.id == supp.log_unit_id.id:
            return 'unit', supp.log_unit_id.id
        elif self.uom_id.id == supp.log_box_id.id:
            return 'box', supp.log_box_id.id
        else:
            raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_id.name))



    #calcula para una cantidad dada, las cantidades en las distintas unidades
    @api.multi
    def get_purchase_unit_conversions(self, qty_uoc, uoc_id, supplier_id):
        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0}
        supp = self.get_product_supp_record(supplier_id)

        cte =  qty_uoc / self._get_unit_ratios(uoc_id, supplier_id)

        res['base'] = float_round(cte * self._get_unit_ratios(supp.log_base_id.id, supplier_id), supp.log_base_id.rounding)
        res['unit'] = float_round(cte * self._get_unit_ratios(supp.log_unit_id.id, supplier_id), supp.log_unit_id.rounding)
        res['box'] = float_round(cte * self._get_unit_ratios(supp.log_box_id.id, supplier_id), supp.log_box_id.rounding)
        return res

    #calcula para una cantidad dada, las cantidades en las distintas unidades
    @api.multi
    def get_sale_unit_conversions(self, qty_uoc, uoc_id):
        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0}
        cte =  qty_uoc / self._get_unit_ratios(uoc_id, 0)

        res['base'] = float_round(cte * self._get_unit_ratios(self.log_base_id.id, 0), self.log_base_id.rounding)
        res['unit'] = float_round(cte * self._get_unit_ratios(self.log_unit_id.id, 0), self.log_unit_id.rounding)
        res['box'] = float_round(cte * self._get_unit_ratios(self.log_box_id.id, 0), self.log_box_id.rounding)
        return res

    #calcula para un precio dado, los precios en las udistintas unidades
    @api.multi
    def get_price_conversions(self, qty_uoc, uoc_id, supplier_id):
        res = {'base': 0.0,
               'unit': 0.0,
               'box': 0.0}
        supp = self.get_product_supp_record(supplier_id)

        cte = qty_uoc * self._get_unit_ratios(uoc_id, supplier_id)

        res['base'] = float_round(cte / self._get_unit_ratios(supp.log_base_id.id, supplier_id), supp.log_base_id.rounding)
        res['unit'] = float_round(cte / self._get_unit_ratios(supp.log_unit_id.id, supplier_id), supp.log_unit_id.rounding)
        res['box'] = float_round(cte / self._get_unit_ratios(supp.log_box_id.id, supplier_id), supp.log_box_id.rounding)
        return res


    #devuelve un factor de conversión a la unidad de stock del producto
    #desde otra unidad (uos_id)
    #qty_en_uom_id= _get_factor(uos_id) x qty_en_uos_id
    @api.multi
    def _get_factor(self, uos_id, supplier_id = 0):

        return self._get_unit_ratios(uos_id, supplier_id)

    #Es funcion devuelve un ratio a la unidad base del producto o uom_id
    #para un proveedor dado
    @api.multi
    def _get_unit_ratios(self, unit, supplier_id):
        uom_id = self.uom_id.id
        res = 1
        if unit == uom_id:
            return res
        if supplier_id == 0 :
            supp = self
            kg_un = supp.kg_un or 1.0
            un_ca = supp.un_ca or 1.0
            ca_ma = supp.ca_ma or 1.0
            ma_pa = supp.ma_pa or 1.0
        else:
            supp = self.get_product_supp_record(supplier_id)
            if supp:
                kg_un = supp.supp_kg_un or 1.0
                un_ca = supp.supp_un_ca or 1.0
                ca_ma = supp.supp_ca_ma or 1.0
                ma_pa = supp.supp_ma_pa or 1.0

            else:
                raise except_orm(_('Error'), _('Supplier_id not in supplier_ids'))
        res = res_uom = 0
        #Paso todo a la unidad de base
        if unit == supp.log_base_id.id:
            res = 1
        if unit == supp.log_unit_id.id:
            res = 1 / (kg_un or 1.0)
        if unit == supp.log_box_id.id:
            res = 1 / ((kg_un or 1.0) * (un_ca or 1.0))
        #Paso la base a la unidad del producto o uom_id
        if uom_id == supp.log_base_id.id:
            res_uom = 1
        if uom_id == supp.log_unit_id.id:
            res_uom = 1 * (kg_un or 1.0)
        if uom_id == supp.log_box_id.id:
            res_uom = 1 * (kg_un * (un_ca or 1.0))
        if res == 0 or res_uom == 0:
            raise except_orm(_('Error'), _('The product unit of measure %s is \
                             not related with any logistic \
                             unit' % self.uom_id.name))

        return res * res_uom
    #Da el factor de conversión entre dos unidades para un determinado
    #proveedor
    @api.multi
    def _conv_units(self, uom_origen, uom_destino, supplier_id):
        res = self._get_unit_ratios(uom_destino, supplier_id) / \
              self._get_unit_ratios(uom_origen, supplier_id)
        return res

    #Sacamos el nombre del codigo/nombre de producto por proveedor
    # si no hay coge producto y le pone un asterisco
    @api.model
    def get_product_supplier_name(self, supplier_id, product_id):

        if not product_id:
            product_id = self.id

        if not supplier_id:
            raise except_orm(_('Error'), _('The product %s is \
                             not related with any supplier \
                             ' % self.uom_id.name))

        suppinfo = self.env['product.supplierinfo'].\
            search([('product_tmpl_id','=',product_id),('name','=', supplier_id)])
        supprod = self.env['product.product'].\
            search([('id','=',product_id)])

        if suppinfo.product_code:
            res_code = suppinfo.product_code and ('['+ suppinfo.product_code +'] ') or ''
        else:
            res_code = supprod.default_code and ('['+ supprod.default_code +']*') or ''

        if suppinfo.product_name:
            res_name = suppinfo.product_name or ''
        else:
            res_name = (supprod.name_template + '*') or ''

        return res_code + res_name

    # sacamos las conversiones de precios,podemos darle un precio
    # para sobreescribir los precios a partir del standar_price
    # habrá que revisarlo en función delos precios y tarifas por proveedor
    @api.multi
    def get_uom_uoc_prices_purchases(self, uoc_id, supplier_id,
                                     custom_price_unit=0.0,
                                     custom_price_udc=0.0):

        custom_price_udc_from_unit = 0.0
        custom_price_unit_from_udc = 0.0
        # Para evitar si hay custom_price_udc, lo pasamos a custom_price_unit
        if custom_price_udc:
            # Si hay lo pasamos a custom price unit para no andar con if
            custom_price_unit_from_udc = \
                self._conv_units(self.uom_id.id, uoc_id, supplier_id) * \
                custom_price_udc

        elif custom_price_unit:
            # Si hay lo pasamos a sacamos custom price udc
            custom_price_udc_from_unit = \
                self._conv_units(uoc_id, self.uom_id.id, supplier_id) * \
                custom_price_unit

        else:
            price_unit = self.standard_price
            price_udc = self._conv_units(uoc_id, self.uom_id.id, supplier_id) \
                * price_unit

        price_udc = custom_price_udc or custom_price_udc_from_unit or price_udc
        price_udc = price_udc
        price_unit = custom_price_unit or custom_price_unit_from_udc or \
            price_unit
        price_unit = price_unit

        return price_unit, price_udc

    @api.multi
    def get_num_mantles(self, uom_qty, total_uom_mantles=False):
        """
        For a uom_qty get the equivalent number of mantles using the logistic
        info, we use the product uom_id because is the default stock unit.
        If uom_mantles is True we return directly the number
        of uom units inside a mantle
        """
        mantles = 0
        uom_in_mantles = 0
        if self.uom_id == self.log_base_id:
            uom_in_mantles = self.kg_un * self.ca_ma * self.un_ca
        elif self.uom_id == self.log_unit_id:
            uom_in_mantles = self.un_ca * self.ca_ma
        elif self.uom_id == self.log_box_id:
            uom_in_mantles = self.ca_ma

        if total_uom_mantles:
            mantles = uom_in_mantles
        elif uom_in_mantles:
            mantles = int(math.ceil(uom_qty / uom_in_mantles))
        return mantles

    @api.multi
    def get_volume_for(self, uom_qty, add_wood_height=False):
        """
        Get the volume for a uom_qty in default product uom_id.
        If add_wood_height True we add this height to the mantle height
        """
        volume = 0.0
        wood_height = 0.0
        num_mantles = self.get_num_mantles(uom_qty)
        if add_wood_height:
            wood_height = self.palet_wood_height
        height_mantles = (self.ma_height * num_mantles) + wood_height
        volume = self.pa_width * self.pa_length * height_mantles
        return volume

    @api.multi
    def get_wood_volume(self):
        """
        Get the volume of a wood used to put under the palet
        """
        width_wood = self.pa_width
        length_wood = self.pa_length
        height_wood = self.palet_wood_height
        return width_wood * length_wood * height_wood


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.model
    def _get_kg_unit(self):
        return self.env.ref('product.product_uom_kgm').id

    @api.model
    def _get_box_unit(self):
        return self.env.ref('midban_product.product_uom_box').id

    @api.model
    def _get_unit_unit(self):
        return self.env.ref('product.product_uom_unit').id

    var_coeff_un = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units')
    var_coeff_ca = fields2.Boolean('Variable coefficient',
                                   help='If checked we can manage'
                                   ' products of variable weight.\n'
                                   'System will not convert between units.')
    log_base_id = fields2.Many2one('product.uom', 'Logistic Base',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic base',
                                   default=_get_kg_unit)
    log_box_id = fields2.Many2one('product.uom', 'Logistic Box',
                                  help='The defined unit of measure will be'
                                  ' related with the logistic unit',
                                  default=_get_box_unit)
    log_unit_id = fields2.Many2one('product.uom', 'Logistic Unit',
                                   help='The defined unit of measure will be'
                                   ' related with the logistic box',
                                   default=_get_unit_unit)

    base_use_purchase = fields2.Boolean('Can be used on purchases',
                                        help='Allows you to buy in the defined'
                                        ' logistic base.')
    unit_use_purchase = fields2.Boolean('Can be used on purchases',
                                        help='Allows you to buy in the defined'
                                        ' logistic unit.', default=True)
    box_use_purchase = fields2.Boolean('Can be used on purchases',
                                       help='Allows you to buy in the defined'
                                       ' logistic box')
    supp_kg_un = fields2.Float("KG/UN Supplier", digits=(4, 2), default = 1.0)
    supp_un_width = fields2.Float("UN Width Supplier", digits=(4, 2))
    supp_un_height = fields2.Float("UN Height Supplier", digits=(4, 2))
    supp_un_length = fields2.Float("UN Length Supplier", digits=(4, 2))
    supp_ca_ma = fields2.Float("CA/MA Supplier", digits=(4, 2), default = 1.0)
    supp_ma_width = fields2.Float("MA Width Supplier", digits=(4, 2))
    supp_ma_height = fields2.Float("MA Height Supplier", digits=(4, 2))
    supp_ma_length = fields2.Float("MA Length Supplier", digits=(4, 2))
    supp_ma_pa = fields2.Float("MA/PA Supplier", digits=(4, 2), default = 1.0)
    supp_pa_width = fields2.Float("PA Width Supplier", digits=(4, 2), default = 0.8)
    supp_pa_height = fields2.Float("PA Height Supplier", digits=(4, 2))
    supp_pa_length = fields2.Float("PA Length Supplier", digits=(4, 2), default = 1.2)
    supp_un_ca = fields2.Float("UN/CA Supplier", digits=(4, 2), default = 1.0)
    supp_ca_width = fields2.Float("CA Width Supplier", digits=(4, 2))
    supp_ca_height = fields2.Float("CA Height Supplier", digits=(4, 2))
    supp_ca_length = fields2.Float("CA Length Supplier", digits=(4, 2))

    is_var_coeff = fields2.Boolean("Variable weight", readonly=True,
                                   compute='_get_is_var_coeff',
                                   store=True,
                                   help="If any conversion is checked, the \
                                   product will be processed as a variable \
                                   weight product in purchases process")

    @api.one
    @api.constrains('log_base_id', 'log_unit_id', 'log_box_id', 'product_uom')
    def check_supplier_uoms(self):

        product_uom = self.product_tmpl_id.uom_id
        if not ((product_uom == self.log_base_id) or
                (product_uom == self.log_unit_id) or
                (product_uom == self.log_box_id)):
            raise Warning(_('The supplit uoms are \
                             not related to product uom\
                             ' % product_uom))

        product_uom = self.product_uom
        if not((product_uom == self.log_base_id) or
                (product_uom == self.log_unit_id) or
                (product_uom == self.log_box_id)):
            raise Warning(_('The supplit uom are \
                             not related to suppplier uoms\
                             ' % product_uom))

    @api.multi
    @api.depends('var_coeff_un', 'var_coeff_ca')
    def _get_is_var_coeff(self):
        """
        Calc name str
        """
        for supp_prod in self:
            supp_prod.is_var_coeff = supp_prod.var_coeff_un or \
                supp_prod.var_coeff_ca


class ProductUom(models.Model):

    _inherit = 'product.uom'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only allowed products for a product
            if product_id is in context."""
        if context is None:
            context = {}
        if context.get('supp_product_id', False) and context.get('supplier_id',
                                                                 False):
            t_prod = self.pool.get('product.product')
            prod = t_prod.browse(cr, uid, context['supp_product_id'], context)
            prod_udc_ids = prod.get_purchase_unit_ids(context['supplier_id'])
            # Because sometimes args = [category = False]
            args = [['id', 'in', prod_udc_ids]]
        elif context.get('product_id', False):
            t_prod = self.pool.get('product.product')
            prod = t_prod.browse(cr, uid, context['product_id'], context)
            product_udv_ids = prod.get_sale_unit_ids()
            # Because sometimes args = [category = False]
            args = [['id', 'in', product_udv_ids]]
        return super(ProductUom, self).search(cr, uid, args,
                                              offset=offset,
                                              limit=limit,
                                              order=order,
                                              context=context,
                                              count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        res = super(ProductUom, self).name_search(name, args=args,
                                                  operator=operator,
                                                  limit=limit)
        if self._context.get('supp_product_id', False) and \
                self._context.get('supplier_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            res = recs.name_get()
        elif self._context.get('product_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            res = recs.name_get()

        return res


class product_category(osv.Model):

    _inherit = "product.category"

    _columns = {
        'code': fields.char('Code', size=12)
    }
