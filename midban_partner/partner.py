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
from openerp.osv import osv, fields, expression
import time
from openerp.tools.translate import _
from openerp import workflow, exceptions
from openerp import models, fields as fields2, api


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


class week_days(osv.Model):
    """ Week days preloaded model to select the supplier service days"""
    _name = "week.days"
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'sequence': fields.integer('Nº day', required=True),
    }


class unregister_partner_reason(osv.Model):
    """ When you unregister a client/supplier a wizard lets you select the
    unregister reason"""
    _name = 'unregister.partner.reason'
    _columns = {
        'name': fields.char('Unregister reason', size=256, required=True),
        'code': fields.char("Code", size=1, required=True)
    }


class time_slot(osv.Model):
    """ Time slot in suppliers and customers to delivery orders"""
    _name = "time.slot"
    _rec_name = "partner_id"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier/Customer'),
        'time_start': fields.float('Start Time', required=True),
        'time_end': fields.float('End Time', required=True),
    }


class call_days_time_slot(osv.Model):
    """ Time slot in suppliers and customers to delivery orders"""
    _name = "call.days.time.slot"
    _rec_name = "partner_id"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier'),
        'day': fields.many2one('week.days', 'Day', required=True),
        'time_start': fields.float('Start Time', required=True),
        'time_end': fields.float('End Time', required=True),
    }


class res_partner(osv.Model):
    _inherit = 'res.partner'
    """ Overwrite display_name column defined in account_report_company and
        all related with it in order to fill display_name colum when a partner
        is created with field active equals to False. This it's necesary if we
        want see partner name in tree and kanaban view."""

    # ATENCIÓN. Completamente sobreescrito para gestionar nombre comercial
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            if record.comercial:
                name=record.comercial
            else:
                name = record.name
            if record.parent_id and not record.is_company:

                name = "%s, %s" % (record.parent_name, name)
            if context.get('show_address_only'):
                name = self._display_address(cr, uid, record, without_company=True, context=context)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res


    # Nedd overwrite because we need overwrite _display_name_store_triggers
    def _display_name_compute(self, cr, uid, ids, name, args, context=None):
        context = dict(context or {})
        context.pop('show_address', None)
        context.pop('show_address_only', None)
        context.pop('show_email', None)
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
                                   ('unregistered', 'Unregistered')],
                                   'Status', readonly=True, required=True,
                                   help="* Validate pending: no validation"
                                   "passed\n"
                                   "* Logistic validation pending: product"
                                   "logistic information has not been"
                                   "reviewed by a manager yet\n"
                                   "* Comercial validation pending: product"
                                   "commercial information (pricing, etc)"
                                   "hasn't been validated by sales manager\n"
                                   "* Validated: both Comercial and logistic"
                                   "validations have been aproved\n"),
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
        'restricted_catalog_ids': fields.many2many('product.product',
                                                   'restricted_catalog_rel',
                                                   'partner_id',
                                                   'product_id',
                                                   'Restricted catalog'),
        'supp_transport_ids': fields.one2many('supplier.transport',
                                              'supplier_id',
                                              'Supplier Transports'),
        'supp_accept_days_ids': fields.many2many('week.days',
                                                 'accept_week_days_rel',
                                                 'partner_id',
                                                 'accept_days_id',
                                                 'Supplier service days'),
        'supp_service_days_ids': fields.many2many('week.days',
                                                  'service_week_days_rel',
                                                  'partner_id',
                                                  'service_days_id',
                                                  'Accept orders days'),
        'reception_method': fields.selection([('mail', 'Mail'),
                                              ('edi', 'EDI'),
                                              ('tlf', 'Tlf'),
                                              ('fax', 'Fax')],
                                             string="Reception Method"),
        'supp_times_delivery': fields.one2many('time.slot', 'partner_id',
                                               'Delivery Time Slots'),
        'delivery_days_ids': fields.many2many('week.days',
                                              'del_week_days_rel',
                                              'partner_id',
                                              'del_days_id',
                                              'Delivery orders days'),
        'group_pickings': fields.boolean('Group pickings by temperature',
                                         help="if checked, when prinnting, \
                                         pickings will be grouped by \
                                         temperature "),
        'invoice_method': fields.selection([('a', 'unknow1'),
                                            ('b', 'unknow2'),
                                            ('c', 'unknow3')],
                                           string="Invoice Method"),
        'times_delivery': fields.one2many('time.slot', 'partner_id',
                                          'Delivery Time Slots'),
        'call_days_slot': fields.one2many('call.days.time.slot', 'partner_id',
                                          'Call Days Time Slot '),
        'ref_history_ids': fields.one2many('res.partner.ref.history',
                                           'partner_id', 'Refs history',
                                           readonly=True),
        'min_palets': fields.integer('Min Palets',
                                     help='Minimum quantity, expresed in '
                                     'palets, needed to the supplier acepts '
                                     'the order')
    }
    _defaults = {
        'active': False,  # it's fixed true when you register a product
        'state2': 'val_pending',
        'reception_method': 'mail',
        'min_palets': 0
    }

    def name_search(self, cr, uid, name, args=None, operator='ilike',
                    context=None, limit=100):
        if not args:
            args = []

        domain = args + ['|', '|', ('ref', '=', name),
                         ('name', operator, name),
                         ('comercial', operator, name)]
        ids = self.search(cr, uid, domain + args,
                              limit=limit, context=context)

        if name and len(ids) == 0:
            partners = super(res_partner, self).name_search(cr, uid, name, args,
                                                            operator, context,
                                                            limit)
            ids = [x[0] for x in partners]

        return self.name_get(cr, uid, ids, context=context)


    def create(self, cr, uid, vals, context=None):
        """
        When a contact is created from a parent partner, validate it
        automatically.
        """
        if not context:
            context = {}
        partner_id = super(res_partner, self).create(cr, uid, vals, context)
        if not vals.get('is_company', False):
            workflow.trg_validate(uid, 'res.partner', partner_id,
                                  'logic_validated', cr)
            workflow.trg_validate(uid, 'res.partner', partner_id,
                                  'commercial_validated', cr)
            workflow.trg_validate(uid, 'res.partner', partner_id,
                                  'active', cr)
        return partner_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if vals.get("ref"):
            ref_history_obj = self.pool["res.partner.ref.history"]
            for partner in self.browse(cr, uid, ids):
                if partner.ref and partner.ref != vals["ref"] and \
                        (vals.get("is_company") or partner.is_company) and \
                        (vals.get("customer") or partner.customer):
                    ref_history_obj.create(cr, uid,
                                           {'partner_id': partner.id,
                                            'old_ref': partner.ref})
        return super(res_partner, self).write(cr, uid, ids, vals,
                                              context=context)

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
            if partner.customer and partner.is_company and not partner.vat:
                raise exceptions.Warning(
                    _('Partner error'),
                    _('Cannot activate a customer without vat'))
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


class resPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('supp_service_days_ids')
    @api.one
    def _compute_distance(self):
        """
        Get the maximum distance between two service days
        """
        def distance(x, y):
            """
            Returns distance between 2 week days. Monday = 1 Sunday = 7
            """
            return (y - x) % 7
        res = 0
        s_days = [x.sequence for x in self.supp_service_days_ids]
        if s_days:
            if len(s_days) == 1:
                res = 7
            elif len(s_days) == 7:
                res = 1
            elif len(s_days) == 6:
                res = 2
            else:
                ctl = True
                init = 0
                end = len(s_days) - 1
                res = 0
                while ctl:
                    x1 = s_days[init]
                    x2 = s_days[init + 1]
                    if distance(x1, x2) >= res:
                        res = distance(x1, x2)
                    if (init + 1) == end:
                        x1 = s_days[0]
                        if distance(x2, x1) >= res:
                            res = distance(x2, x1)
                        ctl = False
                    init += 1
        self.max_distance = res

    # En español porque no coge la traducción en otra clase con la nueva api
    max_distance = fields2.Integer(string='Max. distancia (Días)',
                                   compute='_compute_distance',
                                   help='Máxima distancia entre dos días de '
                                   'servicio adyacentes ',
                                   readonly=True)


class partner_history(osv.Model):
    """ Every time a status change is reached it will be registered in this
    model."""
    _name = 'partner.history'
    _description = "Partner history register changes in partner state2 field"
    _rec_name = "partner_id"
    _order = "date desc"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'partner',
                                      readonly=True, required=True,
                                      ondelete="cascade"),
        'user_id': fields.many2one("res.users", 'User', readonly=True,
                                   required=True),
        'date': fields.datetime('Date', readonly=True, required=True),
        'activity': fields.char('Activity', size=256),
        'reason': fields.char('Reason', size=256),
        'comment': fields.text('Comment')
    }


class ResPartnerRefHistory(osv.Model):

    _name = "res.partner.ref.history"
    _order = "date desc, id desc"

    _columns = {'date': fields.date("Change date", required=True,
                                    readonly=True),
                'partner_id': fields.many2one('res.partner', 'Partner',
                                              required=True,
                                              readonly=True),
                'old_ref': fields.char("Ref", required=True, readonly=True)}

    _defaults = {
        'date': fields.date.context_today
    }
