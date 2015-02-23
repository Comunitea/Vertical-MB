# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
from openerp import tools
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class issue_report(osv.Model):
    _name = "issue.report"
    _description = "Issues Statistics"
    _auto = False
    _rec_name = 'create_date'
    MODELS = [('sale.order', 'Sales'), ('purchase.order', 'Purchases'),
              ('stock.picking', 'Pickings'), ('account.invoice', 'Invoices')]
    _columns = {
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid': fields.many2one("res.users", 'User', readonly=True),
        'flow': fields.reference('Associed Flow',
                                 [('sale.order', 'Sales'),
                                  ('purchase.order', 'Purchases')],
                                 size=128,
                                 readonly=True),
        'object': fields.reference('Object', MODELS, size=128, readonly=True),
        'origin': fields.char('Issue origin', size=128, readonly=True),
        'res_model': fields.selection(MODELS, 'Res Model', readonly=True),
        'res_id': fields.integer('Res ID', readonly=True),
        'edi_message': fields.selection([('desadv2', 'DESADV-2'),
                                         ('recadv', 'RECADV')],
                                        'Edi message',
                                        readonly=True),
        'type_id': fields.many2one('issue.type', 'Type', readonly=True),
        'reason_id': fields.many2one('issue.reason', 'Reason', readonly=True),
        'affected_fields': fields.char('Affected fields',
                                       size=256,
                                       readonly=True),
        'affected_partner_id': fields.many2one('res.partner',
                                               'Affected Client',
                                               readonly=True),
        'caused_partner_id': fields.many2one('res.partner',
                                             'Caused Partner',
                                             readonly=True),
        'automatic': fields.boolean('Automatic'),
        'solution': fields.char('Solution', size=256, readonly=True),
        'categ_id': fields.many2one('product.category',
                                    'Category',
                                    readonly=True),
        'product_id': fields.many2one('product.product',
                                      'Product',
                                      readonly=True),
        'product_qty': fields.float('Quantity',
                                    digits_compute=
                                    dp.get_precision('Product UoS'),
                                    readonly=True),
        'uom_id': fields.many2one('product.uom',
                                  'Unit of Measure',
                                  readonly=True),
        'issue_id': fields.many2one('issue', 'Issue', readonly=True)
    }
    _order = 'create_date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'issue_report')
        cr.execute("""
            create or replace view issue_report as (
            select row_number() over (order by s.create_date) as id,
            t.categ_id,
            l.product_id,
            l.product_qty,
            t.uom_id,
            s.id as issue_id,
            s.create_date,
            s.affected_partner_id,
            s.caused_partner_id,
            s.affected_fields,
            s.create_uid,
            s.flow,
            s.object,
            s.origin,
            s.res_model,
            s.res_id,
            s.edi_message,
            s.type_id,
            s.reason_id,
            s.automatic,
            s.solution
            FROM product_info l
            RIGHT JOIN issue s ON s.id  =l.issue_id
            LEFT JOIN product_product p ON l.product_id = p.id
            LEFT JOIN product_template t ON p.product_tmpl_id = t.id
            LEFT JOIN product_uom u ON u.id = l.uom_id
            LEFT JOIN product_uom u2 ON u2.id = t.uom_id
            )""")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
