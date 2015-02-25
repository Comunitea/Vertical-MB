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
# from openerp.osv import osv, fields
# from datetime import datetime, timedelta


# class purchase_order(osv.Model):
#     _inherit = "purchase.order"

#     def _get_next_working_date(self, cr, uid, context=None):
#         """
#         Returns the next working day date respect today
#         """
#         today = datetime.now()
#         week_day = today.weekday()  # Monday 0 Sunday 6
#         delta = 1
#         if week_day == 4:
#             delta = 3
#         elif week_day == 5:
#             delta = 2
#         new_date = today + timedelta(days=delta or 0.0)
#         date_part = datetime.strftime(new_date, "%Y-%m-%d")
#         res = datetime.strptime(date_part + " " + "22:59:59",
#                                 "%Y-%m-%d %H:%M:%S")
#         return res

#     _columns = {
#         'date_planned': fields.datetime('Scheduled Date', required=True,
#                                         select=True,
#                                         help="Date propaged to shecduled \
#                                               date of related picking"),
#     }
#     _defaults = {
#         'date_planned': _get_next_working_date,
#     }

#     def create(self, cr, uid, vals, context=None):
#         if context is None:
#             context = {}
#         po_id = super(purchase_order, self).create(cr, uid, vals, context)
#         if po_id:
#             po_obj = self.browse(cr, uid, po_id, context)
#             for line in po_obj.order_line:
#                 line.write({'date_planned': po_obj.date_planned})
#         return po_id

#     def write(self, cr, uid, ids, vals, context=None):
#         if context is None:
#             context = {}
#         res = super(purchase_order, self).write(cr, uid, ids, vals, context)
#         for po in self.browse(cr, uid, ids, context):
#             for line in po.order_line:
#                 line.write({'date_planned': po.date_planned})
#         return res


# class purchase_order_line(osv.Model):
#     _inherit = "purchase.order.line"

#     def _get_date_planned(self, cr, uid, supplier_info, date_order_str,
#                           context=None):
#         """
#         Overwrited.
#         Returns the next working day date respect today
#         """
#         today = datetime.now()
#         week_day = today.weekday()  # Monday 0 Sunday 6
#         delta = 1
#         if week_day == 4:
#             delta = 3
#         elif week_day == 5:
#             delta = 2
#         new_date = today + timedelta(days=delta or 0.0)
#         date_part = datetime.strftime(new_date, "%Y-%m-%d")
#         res = datetime.strptime(date_part + " " + "22:59:59",
#                                 "%Y-%m-%d %H:%M:%S")
#         return res
