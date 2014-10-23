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

from openerp import tools
from openerp.osv import fields, osv


class sale_report(osv.osv):
    _name = "wave.report"
    _description = "Group picks of waves"
    _auto = False
    _rec_name = 'product_id'

    def _get_units_and_boxes(self, cr, uid, ids, field_names, args,
                             context=None):
        if context is None:
            context = {}
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = {}
            qty = item.product_qty
            un_ca = item.product_id.un_ca
            num_boxes = 0
            while qty >= un_ca:
                qty -= un_ca
                num_boxes += 1
            res[item.id]['units'] = qty
            res[item.id]['boxes'] = num_boxes
        return res

    _columns = {
        'product_id': fields.many2one('product.product', 'Product',
                                      readonly=True),
        'reference': fields.related('product_id', 'default_code', type='char',
                                    string='Reference', size=128,
                                    readonly=True),
        'ean13': fields.related('product_id', 'ean13', type='char',
                                string='EAN 13', size=128, readonly=True),
        'location_id': fields.many2one('stock.location', 'Location',
                                       readonly=True),
        'product_qty': fields.float('Quantity', readonly=True),
        'units': fields.function(_get_units_and_boxes, type='integer',
                                 multi='mult', string='Units', readonly=True),
        'boxes': fields.function(_get_units_and_boxes, type='integer',
                                 multi='mult', string='Boxes', readonly=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot',
                                  readonly=True),
        'wave_id': fields.many2one('stock.picking.wave', 'Wave', readonly=True)
    }

    # def _select(self):
    #     select_str = """
    #         SELECT min(SM.id) as id,
    #                SM.product_id as product_id,
    #                L.id as location_id,
    #                sum(SM.product_uom_qty) as product_qty,
    #                P.wave_id as wave_id
    #     """
    #     return select_str

    # def _from(self):
    #     from_str = """
    #         stock_move SM
    #             INNER JOIN product_template PR on PR.id = SM.product_id
    #             INNER JOIN stock_location L on L.id = PR.picking_location_id
    #             INNER JOIN stock_picking P on P.id = SM.picking_id
    #     """
    #     return from_str

    # def _group_by(self):
    #     group_by_str = """
    #         GROUP BY SM.product_id,
    #                  L.id,
    #                  P.wave_id
    #     """
    #     return group_by_str

    # def init(self, cr):
    #     # self._table = sale_report
    #     tools.drop_view_if_exists(cr, self._table)
    #     cr.execute("""CREATE or REPLACE VIEW %s as (
    #         %s
    #         FROM ( %s )
    #         %s
    #         UNION
    #         %s
    #         FROM %s
    #         %s
    #         )""" % (self._table, self._select(), self._from(),
    #                 self._group_by()))

    def _select1(self):
        select_str = """
            SELECT min(OP.id) as id,
                   Q.product_id as product_id,
                   Q.lot_id as lot_id,
                   OP.location_id ,
                   sum(Q.qty) as product_qty,
                   W.id as wave_id
        """
        return select_str

    def _from1(self):
        from_str = """
            stock_quant Q
                INNER JOIN stock_quant_package PA on PA.id = Q.package_id
                INNER JOIN stock_pack_operation OP on OP.package_id = PA.id
                INNER JOIN stock_picking P on P.id = OP.picking_id
                INNER JOIN stock_picking_wave W on W.id = P.wave_id
            WHERE OP.product_id is null
        """
        return from_str

    def _group_by1(self):
        group_by_str = """
            GROUP BY
                Q.product_id,
                Q.lot_id,
                OP.location_id,
                W.id
        """
        return group_by_str

    def _select2(self):
        select_str = """
            SELECT min(OP.id) as id,
                   OP.product_id as product_id,
                   OP.lot_id as lot_id,
                   OP.location_id ,
                   sum(OP.product_qty) as product_qty,
                   W.id as wave_id
        """
        return select_str

    def _from2(self):
        from_str = """
            stock_pack_operation OP
                INNER JOIN stock_picking P on P.id = OP.picking_id
                INNER JOIN stock_picking_wave W on W.id = P.wave_id
            WHERE OP.product_id is not null
        """
        return from_str

    def _group_by2(self):
        group_by_str = """
            GROUP BY
                OP.product_id,
                OP.lot_id,
                OP.location_id,
                W.id
        """
        return group_by_str

    def init(self, cr):
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            %s
            UNION
            %s
            FROM %s
            %s
            )""" % (self._table, self._select1(), self._from1(),
                    self._group_by1(),
                    self._select2(), self._from2(), self._group_by2()
                    ))
