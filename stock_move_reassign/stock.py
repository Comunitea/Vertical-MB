# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
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
from openerp import models, fields, api
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm
import time
import logging
_logger = logging.getLogger(__name__)

class stock_move(models.Model):

    _inherit = "stock.move"

    partner_id2 = fields.Many2one('res.partner', string='Customer',
                                  related='picking_id.partner_id',
                                  readonly=True,
                                  store=True)
    # trans_route_id2 = fields.Many2one('route',
    #                                   related='picking_id.trans_route_id',
    #                                   store=True)
    # route_detail_id2 = fields.Many2one('route.detail',
    #                                    related='picking_id.route_detail_id',
    #                                    store=True)
