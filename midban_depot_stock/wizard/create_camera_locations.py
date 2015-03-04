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
from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class create_camera_locations(models.TransientModel):
    _name = 'create.camera.locations'

    aisle_ids = fields.One2many('aisle.record', 'wzd_id', 'Aisles Config')

    @api.one
    def create_locations(self):
        raise except_orm(_('Error'), _('Aun no esta hecho primine'))
        return


class aisle_record(models.TransientModel):
    _name = "aisle.record"
    _rec_name = "aisle_num"

    @api.one
    @api.onchange('num_cols', 'num_heights', 'num_subcols', 'pick_heights')
    def _calc_ubications_totals(self):
        """
        """
        nc = self.num_cols
        nh = self.num_heights
        ns = self.num_subcols or 1
        ph = self.pick_heights
        self.storage_heights = nh - ph
        self.total_pick_locs = nc * ph * ns
        self.total_store_locs = nc * self.storage_heights * ns
        self.total_locs = nc * nh * ns

    wzd_id = fields.Many2one('create.camera.locations', 'Wizard id')
    aisle_num = fields.Integer('Aisle number', required=True)
    num_cols = fields.Integer('Columns', required=True)
    num_heights = fields.Integer('Heights', required=True)
    num_subcols = fields.Integer('Subcolumns', required=True)
    pick_heights = fields.Integer('Pick heights', required=True)
    storage_heights = fields.Integer('Storage heights', readonly=True,)
    total_pick_locs = fields.Integer('Picking locations', readonly=True)
    total_store_locs = fields.Integer('Storage locations', readonly=True)
    total_locs = fields.Integer('Total Locations', readonly=True)
    my_length = fields.Float('Length', default=1.30, required=True)
    my_width = fields.Float('Width', default=0.9, required=True)
    my_height = fields.Float('Height', default=2.5, required=True)
