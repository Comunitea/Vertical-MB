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
import time
from openerp.tools.translate import _
from openerp import workflow


class supplier_transport(osv.Model):
    """ Supplier transports. In suppliers view you can select it.
    Transpors must be unique for partners."""
    _name = "supplier.transport"
    _description = "Supplier Transports"
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'npalets': fields.integer('Number of palets', required=True),
        'usable_height': fields.float('Usable height', digits=(4, 2),
                                      required=True),
        'supplier_id': fields.many2one('res.partner', 'Supplier'),
    }


class supplier_service_days(osv.Model):
    """ Week days preloaded model to select the supplier service days"""
    _name = "supplier.service.days"
    _columns = {
        'name': fields.char('Name', size=128, required=True),
    }


class unregister_partner_reason(osv.Model):
    """ When you unregister a client/supplier a wizard lets you select the
    unregister reason"""
    _name = 'unregister.partner.reason'
    _columns = {
        'name': fields.char('Unregister reason', size=256, required=True),
    }


class res_partner(osv.Model):
    _inherit = 'res.partner'
    """ Overwrite display_name column defined in account_report_company and
        all related with it in order to fill display_name colum when a partner
        is created with field active equals to False. This it's necesary if we
        want see partner name in tree and kanaban view."""

    # Nedd overwrite because we need overwrite _display_name_store_triggers
    def _display_name_compute(self, cr, uid, ids, name, args, context=None):
        context = dict(context or {})
        context.pop('show_address', None)
        return dict(self.name_get(cr, uid, ids, context=context))

    # Overwrite necesary to fill display_name column propertly.
    # we add ('active', '=', False) to the domain
    _display_name_store_triggers = {
        'res.partner': (lambda self, cr, uid, ids, context=None:
                        self.search(cr, uid, [('id', 'child_of', ids), '|',
                                              ('active', '=', True),
                                              ('active', '=', False)]),
                        ['parent_id', 'is_company', 'name',
                         'firstname', 'lastname'], 10)
    }
    # Nedd overwrite because we need overwrite _display_name_store_triggers
    _display_name = lambda self, *args, **kwargs: self._display_name_compute(
        *args, **kwargs)

    _columns = {

        'state2': fields.selection([
                                   ('val_pending', 'Validate pending'),
                                   ('logic_pending',
                                    'Logistic validation pending'),
                                   ('commercial_pending',
                                    'Comercial validation pending'),
                                   ('validated', 'Validated'),
                                   ('registered', 'Registered'),
                                   ('unregistered', 'unregistered')],
                                   'Status', readonly=True, required=True),
        # Active only can be changed through register/unregister buttons
        'active': fields.boolean('Active', readonly=True),
        'history_ids': fields.one2many('partner.history', 'partner_id',
                                       'Partner History'),
        'display_name': fields.function(_display_name, type='char',
                                        string='Name',
                                        store=_display_name_store_triggers),
        'unregister_reason_id': fields.many2one('unregister.partner.reason',
                                                'Unregister Reason',
                                                readonly=True),
        'supp_transport_ids': fields.one2many('supplier.transport',
                                              'supplier_id',
                                              'Supplier Transports'),
        'supp_service_days_ids': fields.many2many('supplier.service.days',
                                                  'supplier_service_days_rel',
                                                  'partner_id',
                                                  'service_days_id',
                                                  'Supplier service days'),
        'restricted_catalog_ids': fields.many2many('product.product',
                                                   'restricted_catalog_rel',
                                                   'partner_id',
                                                   'product_id',
                                                   'Restricted catalog'),
    }
    _defaults = {
        'active': False,  # it's fixed true when you register a product
        'state2': 'val_pending',
    }

    def create(self, cr, uid, vals, context=None):
        """
        When a contact is created from a parent partner, validate it
        automatically.
        """
        if not context:
            context = {}
        partner_id = super(res_partner, self).create(cr, uid, vals, context)
        if vals.get('parent_id', False):
            workflow.trg_validate(uid, 'res.partner', partner_id,
                                  'logic_validated', cr)
            workflow.trg_validate(uid, 'res.partner', partner_id,
                                  'commercial_validated', cr)
            workflow.trg_validate(uid, 'res.partner', partner_id,
                                  'active', cr)
        return partner_id

    def _update_history(self, cr, uid, ids, context, partner_obj, activity):
        """ Update partner history model for the argument partner_obj whith
            the activity defined in activity argument"""
        vals = {
            'partner_id': partner_obj.id,
            'user_id': uid,
            'date': time.strftime("%Y-%m-%d %H:%M:%S"),
            'activity': activity
        }
        self.pool.get("partner.history").create(cr, uid, vals, context)
        return True

    def act_validate_pending(self, cr, uid, ids, context=None):
        """ Fix state in validate pending, partner no active, update history"""
        for partner in self.pool.get("res.partner").browse(cr, uid, ids):
            partner.write({'state2': 'val_pending', 'active': False})
            message = _("Pending logistic and commercial validate")
            self._update_history(cr, uid, ids, context, partner, message)
        return True

    def act_comercial_pending(self, cr, uid, ids, context=None):
        """ Fix state in commercial pending, partner no active,
            update history. It's a flow method"""
        for partner in self.pool.get("res.partner").browse(cr, uid, ids):
            message = _("Logistic validate done")
            self._update_history(cr, uid, ids, context, partner, message)
            partner.write({'state2': 'commercial_pending', 'active': False})
        return True

    def act_logic_pending(self, cr, uid, ids, context=None):
        """ Fix state in logic pending, partner no active,
            update history. It's a flow method"""
        for partner in self.pool.get("res.partner").browse(cr, uid, ids):
            message = _("Comercial validate done")
            self._update_history(cr, uid, ids, context, partner, message)
            partner.write({'state2': 'logic_pending', 'active': False})
        return True

    def act_validated(self, cr, uid, ids, context=None):
        """ Fix state in validated, partner no active,
            update history. It's a flow method"""
        for partner in self.pool.get("res.partner").browse(cr, uid, ids):
            message = _("Comercial and validate done. Pending to register")
            self._update_history(cr, uid, ids, context, partner, message)
            partner.write({'state2': 'validated', 'active': False})
        return True

    def act_active(self, cr, uid, ids, context=None):
        """ Fix state in registered, partner active,
            update history. It's a flow method"""
        for partner in self.pool.get("res.partner").browse(cr, uid, ids):
            message = _("Registered")
            self._update_history(cr, uid, ids, context, partner, message)
            partner.write({'state2': 'registered', 'active': True})
        return True

    def register_again(self, cr, uid, ids, context=None):
        """ Fix state in registered, partner active,
            update history. It's a button method"""
        for partner in self.pool.get("res.partner").browse(cr, uid, ids):
            message = _("Registered again")
            self._update_history(cr, uid, ids, context, partner, message)
            partner.write({'state2': 'registered', 'active': True})
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        """ Overwrites copy methos in order to no duplicate the history,
        transports and unregister reason"""
        default = {} if default is None else default.copy()
        default.update({
            'history_ids': [],
            'supp_transport_ids': [],
            'unregister_reason_id': False
        })
        return super(res_partner, self).copy(cr, uid, id, default=default,
                                             context=context)


class partner_history(osv.Model):
    """ Every time a status change is reached it will be registered in this
    model."""
    _name = 'partner.history'
    _description = "Partner history register changes in partner state2 field"
    _rec_name = "partner_id"
    _order = "date desc"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'partner',
                                      readonly=True, required=True),
        'user_id': fields.many2one("res.users", 'User', readonly=True,
                                   required=True),
        'date': fields.datetime('Date', readonly=True, required=True),
        'activity': fields.char('Activity', size=256),
        'reason': fields.char('Reason', size=256),
        'comment': fields.text('Comment')
    }
