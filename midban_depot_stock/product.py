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
from openerp.tools.translate import _


class product_putaway_strategy(osv.osv):
    _inherit = 'product.putaway'

    def _get_putaway_options(self, cr, uid, context=None):
        """
        Overwrite to define a Midban custom putaway strategu for
        storage location
        """
        if context is None:
            context = {}
        import ipdb; ipdb.set_trace()
        sup = super(product_putaway_strategy, self)
        res = sup._get_putaway_options(cr, uid, context)
        res.extend([('midban_storage', 'Midban Storage')])
        return res

    def putaway_apply(self, cr, uid, putaway_strat, product, context=None):
        """
        Define the strategy to move product from input location (beach)
        to a specific storage location.
        This function is called in _prepare_pack_ops in stock.picking
        """
        if context is None:
            context = {}
        sup = super(product_putaway_strategy, self)
        res = sup.putaway_apply(cr, uid, putaway_strat, product,
                                context=context)

        if putaway_strat.method == 'midban_storage':
            res = res
        return res

    _columns = {
        'method': fields.selection(_get_putaway_options, "Method",
                                   required=True),
    }


class product_template(osv.Model):
    """
    Adding field picking location
    """
    _inherit = "product.template"

    _columns = {
        'picking_location_id': fields.many2one('stock.location',
                                               'Location Picking',
                                               required=True,
                                               domain=[('usage', '=',
                                                        'internal')]),
    }
    _sql_constraints = [
        ('location_id_uniq', 'unique(picking_location_id)',
         _("Field Location picking is already setted"))
    ]
