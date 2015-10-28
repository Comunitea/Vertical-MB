# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@comunitea.com>$
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
from openerp import models, fields, api, exceptions, _
from datetime import datetime

class product_template(models.Model):

    _inherit = 'product.template'

    max_discount = fields.Float('Max discount', help='Maximum discount for sales')
    last_edit = fields.Datetime('Last edit', help='Last edition of max discount')
    category_max_discount = fields.Float(string='Category max discount', related='categ_id.max_discount', readonly="1")

    @api.model
    def create(self, vals):
        if vals.get('max_discount', False):
            vals['last_edit'] = datetime.now()
        return super(product_template, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('max_discount', False):
            vals['last_edit'] = datetime.now()
        return super(product_template, self).write(vals)


class product_category(models.Model):

    _inherit = 'product.category'

    max_discount = fields.Float('Max discount', help='Maximum discount for sales')
    last_edit = fields.Datetime('Last edit', help='Last edition of max discount')

    @api.model
    def create(self, vals):
        if vals.get('max_discount', False):
            vals['last_edit'] = datetime.now()
        return super(product_category, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('max_discount', False):
            vals['last_edit'] = datetime.now()
        return super(product_category, self).write(vals)
