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
    _name = "process.cross.dock.wzd"
    _columns = {
        'mode': fields.selection([('midban', 'Midban products'),
                                  ('cross_dock', 'Cross Docks products'),
                                  ('both', 'Midban and cross dock products')],
                                 string="Create purchases for",
                                 required=True)

    }

    def create_delayed_purchases(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # t_proc = self.pool.get('procurement.order')
        procurement_ids = []
        # domain = []
        # wzd_obj = self.browse(cr, uid, ids[0], context=context)

        # if wzd.obj.mode in ['midban', 'both']:
        #     domain =
        # if wzd.obj.mode in ['cross_dock', 'both']:

        # if domain:
        #     procurement_ids = t_proc.search(cr, uid, domain, context=context)
        if not procurement_ids:
            raise osv.except_osv(_('Error!'), _('No purchases to create.'))
        return
