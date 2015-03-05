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
from openerp.osv import osv, fields
from datetime import datetime, timedelta


class product_template(osv.Model):
    _inherit = "product.template"
    _columns = {
        'min_rotation': fields.float('Mín. rotation'),
        'under_rotation': fields.boolean('Under Rotation', readonly=True),
        'rotation': fields.float('Mín. rotation', readonly=True),
    }
    _defaults = {
        'min_rotation': 0.00,
        'under_rotation': False
    }

    def _get_num_sum(self, cr, uid, ids, dayw, context=None):
        if dayw == 1:
            return 6
        if dayw == 2:
            return 5
        if dayw == 3:
            return 4
        if dayw == 4:
            return 3
        if dayw == 5:
            return 2
        if dayw == 6:
            return 1
        if dayw == 7:
            return 0

    def _get_num_deduct(self, cr, uid, ids, dayw, context=None):
        if dayw == 1:
            return 0
        if dayw == 2:
            return -1
        if dayw == 3:
            return -2
        if dayw == 4:
            return -3
        if dayw == 5:
            return -4
        if dayw == 6:
            return -5
        if dayw == 7:
            return -6

    def _format_dates(self, cr, uid, ids, date, start=False, context=None):
        day_week = date.isoweekday()
        strtime = ''
        if start:
            ndeduct = self._get_num_deduct(cr, uid, ids,
                                           day_week, context=context)
            strtime = ' 00:00:01'
        else:
            ndeduct = self._get_num_sum(cr, uid, ids,
                                        day_week, context=context)
            strtime = ' 23:59:59'
        date = date + timedelta(days=ndeduct)

        return str(date.year) + '-' + str(date.month).zfill(2) + \
            '-' + str(date.day).zfill(2) + strtime

    def get_products_low_rotation(self, cr, uid, ids, context=None):
        """
        Function that checks what products are below the minimum
        rotation and puts them one True boolean field to filter them.
        """
        if context is None:
            context = {}
        product = self.pool.get('product.product')
        user = self.pool.get('res.users').browse(cr, uid, uid)

        for product_id in product.search(cr, uid, []):
            current_date = datetime.now() - timedelta(weeks=1)
            rotation = 0.0
            for x in range(0, 4):
                date_start = self._format_dates(cr, uid, ids, current_date,
                                                True, context=context)
                date_stop = self._format_dates(cr, uid, ids, current_date,
                                               False, context=context)
                cr.execute("SELECT \
                            sum(m.product_qty * pu.factor / pu2.factor) \
                            FROM stock_move m \
                            INNER JOIN stock_picking s ON s.id=m.picking_id \
                            INNER JOIN stock_picking_type pt on S.picking_type_id=pt.id \
                            INNER JOIN product_product p ON p.id=m.product_id \
                            INNER JOIN product_template pt \
                            ON (p.product_tmpl_id=pt.id) \
                            INNER JOIN product_uom pu ON (pt.uom_id=pu.id) \
                            INNER JOIN product_uom pu2 \
                            ON (m.product_uom=pu2.id) \
                            WHERE m.state='done' \
                            AND pt.code='outgoing' \
                            AND m.date>=%s \
                            AND m.date<=%s \
                            AND m.product_id=%s \
                            AND m.company_id=%s",
                           (date_start, date_stop, str(product_id),
                            str(user.company_id.id)))
                res = cr.fetchall()[0][0]
                if res is None:
                    res = 0.0
                rotation += res
                current_date = current_date - timedelta(weeks=1)

            rotation = rotation / 4

            prod = product.browse(cr, uid, product_id)
            if prod.min_rotation > 0 and prod.min_rotation > rotation:
                product.write(cr, uid, prod.id, {'under_rotation': True,
                                                 'rotation': rotation})
            elif prod.min_rotation > 0 and prod.min_rotation < rotation:
                product.write(cr, uid, prod.id, {'under_rotation': False,
                                                 'rotation': 0.0})
            elif (prod.categ_id.min_rotation > 0 and
                  prod.categ_id.min_rotation > rotation):
                product.write(cr, uid, prod.id, {'under_rotation': True,
                                                 'rotation': rotation})
            elif (prod.categ_id.min_rotation > 0 and
                  prod.categ_id.min_rotation < rotation):
                product.write(cr, uid, prod.id, {'under_rotation': False,
                                                 'rotation': 0.0})
        return True
