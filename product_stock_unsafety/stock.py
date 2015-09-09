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
from openerp import api, models, fields


class stock_config_settings(models.TransientModel):
    _inherit = 'stock.config.settings'

    configured_period_last_year = \
        fields.Integer('Stock days period',
                       help='Stock days period')
    configured_period_adjustement = \
        fields.Integer('Stock days adjustement period',
                       help='Asjustement period')

    @api.multi
    def get_default_configured_period_last_year(self, fields):
        domain = [('key', '=', 'configured.period.last.year')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = int(param_obj.value)
        return {'configured_period_last_year': value}

    @api.multi
    def set_configured_period_last_year(self):
        domain = [('key', '=', 'configured.period.last.year')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = str(self.configured_period_last_year)

    @api.multi
    def get_default_configured_period_adjustement(self, fields):
        domain = [('key', '=', 'configured.period.adjustement')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        value = int(param_obj.value)
        return {'configured_period_adjustement': value}

    @api.multi
    def set_configured_period_adjustement(self):
        domain = [('key', '=', 'configured.period.adjustement')]
        param_obj = self.env['ir.config_parameter'].search(domain)
        param_obj.value = str(self.configured_period_adjustement)
