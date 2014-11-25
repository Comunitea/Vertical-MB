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
from openerp.tools.translate import _


class process_cross_dock_wzd(osv.TransientModel):
    """
    Wizard to create purchases orders of cross dock products.
    """
    _name = "process.cross.dock.wzd"
    _columns = {
        'mode': fields.selection([('midban', 'Midban products'),
                                  ('cross_dock', 'Cross Docks products'),
                                  ('both', 'Midban and cross dock products')],
                                 string="Create purchases for",
                                 required=True,
                                 help="Choose if you want to create purchase \
                                 orders for MIDBAN, for cross-dock supplier \
                                 or for both of them")

    }
    _default = {
        'mode': 'both',
    }

    def _get_cross_dock_purchases(self, cr, uid, proc_ids, context=None):
        """
        Create a purchases for Cross dock products.
        We will create a purchase order for each supplier and assign a drop
        code.
        make_po seems only work well with one procurement each time.
        """
        if context is None:
            context = {}
        purchase_ids = []
        t_proc = self.pool.get('procurement.order')
        t_po = self.pool.get('purchase.order')
        for proc_id in proc_ids:
            t_proc.make_po(cr, uid, proc_id, context=context)
        for proc in t_proc.browse(cr, uid, proc_ids, context=context):
            if proc.purchase_id:
                proc.write({'buy_later': False}, context=context)
                purchase_ids.append(proc.purchase_id.id)
        purchase_ids = list(set(purchase_ids))
        t_po.signal_workflow(cr, uid, purchase_ids, 'purchase_confirm')
        return purchase_ids

    def _get_midban_purchases(self, cr, uid, proc_ids, context=None):
        """
        Create a purchases for Cross dock products.
        We will create a purchase order for each transport route and assign a
        drop code.
        """
        if context is None:
            context = {}
        purchase_ids = []
        t_proc = self.pool.get('procurement.order')
        t_po = self.pool.get('purchase.order')
        procs_by_route = {}
        for proc in t_proc.browse(cr, uid, proc_ids, context=context):
            if proc.trans_route_id.id in procs_by_route.keys():
                procs_by_route[proc.trans_route_id.id].append(proc.id)
            else:
                procs_by_route[proc.trans_route_id.id] = [proc.id]
        if procs_by_route:
            for key in procs_by_route.keys():
                new_ids = procs_by_route[key]
                to_confirm_ids = []
                # Create Purchases
                for proc_id in new_ids:
                    # proc = t_proc.browse(cr, uid, proc_id, context=context)
                    t_proc.make_po(cr, uid, proc_id, context=context)
                # Get the related purchases
                for proc in t_proc.browse(cr, uid, new_ids, context=context):
                    if proc.purchase_id:
                        proc.write({'buy_later': False}, context=context)
                        purchase_ids.append(proc.purchase_id.id)
                        to_confirm_ids.append(proc.purchase_id.id)
                 # Confirm the related purchases to the route
                to_confirm_ids = list(set(purchase_ids))
                t_po.signal_workflow(cr, uid, to_confirm_ids,
                                     'purchase_confirm')
        purchase_ids = list(set(purchase_ids))
        return list(set(purchase_ids))

    def create_delayed_purchases(self, cr, uid, ids, context=None):
        """
        Create purchase orders for products that came from midban regulator
        warehouse or from cross-dock suppliers. The procurements related are
        marked as 'buy later'.
        If we are processing midban products we will group purchase orders by
        transport routhe, else we group them by partner.
        """
        if context is None:
            context = {}
        # import ipdb; ipdb.set_trace()
        t_proc = self.pool.get('procurement.order')
        proc_ids = []
        purchase_ids = []
        wzd_obj = self.browse(cr, uid, ids[0], context=context)
        # Process Midban Products. The principal supplier is a regulator
        if wzd_obj.mode in ['midban', 'both']:
            # domain += [('product_id.seller_id.regulator', '=', True)]
            domain = [('state', '=', 'running'), ('buy_later', '=', True),
                      ('product_id.seller_id.regulator', '=', True),
                      ('trans_route_id', '!=', False)]
            proc_ids = t_proc.search(cr, uid, domain, context=context)
            purchase_ids += self._get_midban_purchases(cr, uid, proc_ids,
                                                       context=context)

        # Process Cross Dock. The principal supplier is not a regulator
        if wzd_obj.mode in ['cross_dock', 'both']:
            domain = [('state', '=', 'running'), ('buy_later', '=', True),
                      ('product_id.seller_id.regulator', '=', False),
                      ('trans_route_id', '!=', False)]
            proc_ids = t_proc.search(cr, uid, domain, context=context)
            purchase_ids += self._get_cross_dock_purchases(cr, uid, proc_ids,
                                                           context=context)
        if not purchase_ids:
            raise osv.except_osv(_('Error!'), _('No purchases created.'))

        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference(cr, uid, 'purchase',
                                            'purchase_form_action')
        action = self.pool.get(res[0]).read(cr, uid, res[1],
                                            context=context)
        action['domain'] = str([('id', 'in', purchase_ids)])
        return action
