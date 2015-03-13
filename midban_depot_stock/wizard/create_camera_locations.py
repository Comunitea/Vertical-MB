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
import itertools


class create_camera_locations(models.TransientModel):
    _name = 'create.camera.locations'

    aisle_ids = fields.One2many('aisle.record', 'wzd_id', 'Aisles Config')
    camera_code = fields.Char('Camera Code', required=True)

    def _get_my_cartesian_product(self, r_col, r_hei, r_sub):
        lsts = []
        res = []
        if r_col:
            lsts.append(r_col)
        if r_hei:
            lsts.append(r_hei)
        if r_sub:
            lsts.append(r_sub)

        if len(lsts) == 1:
            res = list(itertools.product(lsts[0]))
        if len(lsts) == 2:
            res = list(itertools.product(lsts[0], lsts[1]))
        if len(lsts) == 3:
            res = list(itertools.product(lsts[0], lsts[1], lsts[2]))
        return res

    def _create_camera_zone(self, camera_obj):
        """
        Create a storage zone and a pickinf zone chil of camera obj
        """
        vals = {
            'location_id': camera_obj.id,
            'usage': 'view',
            'temp_type_id': camera_obj.temp_type_id.id,
            'width': 100,
            'length': 100,
            'height': 100,
        }
        vals2 = vals
        vals2.update({'name': self.camera_code + ' Picking',
                      'zone': 'picking'})
        pick = self.env['stock.location'].create(vals2)
        vals2 = vals
        vals2.update({'name': self.camera_code + ' Almacenaje ',
                      'zone': 'storage'})
        store = self.env['stock.location'].create(vals2)
        return pick, store

    def _get_locations_vals(self, item, camera_obj, pick_zone_obj,
                            store_zone_obj):
        """
        Return a list of dict containing vals of the new locations
        """
        res = []

        r_col = [str(x + 1) for x in range(item.num_cols)]
        r_pick = [str(x + 1) for x in range(item.pick_heights)]
        st_heights = item.num_heights - item.pick_heights
        r_store = [str(item.pick_heights + x + 1) for x in range(st_heights)]
        r_subcol = [str(x + 1) for x in range(item.num_subcols)]

        pick_tuples = self._get_my_cartesian_product(r_col, r_pick, r_subcol)
        pick_names = ['/'.join(x) for x in pick_tuples]

        store_tuples = self._get_my_cartesian_product(r_col, r_store, r_subcol)
        store_names = ['/'.join(x) for x in store_tuples]
        # Create Picking vals
        for name in pick_names:
            vals = {
                'usage': 'internal',
                'temp_type_id': camera_obj.temp_type_id.id,
                'width': item.my_width,
                'length': item.my_length,
                'height': item.my_height,
                'name': str(item.aisle_num) + '/' + name,
                'location_id': pick_zone_obj.id,
                'zone': 'picking',
            }
            res.append(vals)
        # Create Store vals
        for name in store_names:
            vals = {
                'usage': 'internal',
                'temp_type_id': camera_obj.temp_type_id.id,
                'width': item.my_width,
                'length': item.my_length,
                'height': item.my_height,
                'name': str(item.aisle_num) + '/' + name,
                'location_id': store_zone_obj.id,
                'zone': 'storage',
            }
            res.append(vals)
        return res

    @api.multi
    def create_locations(self):
        active_id = self._context.get('active_id', False)
        if not active_id:
            raise except_orm(_('Error'), _('Not camera defined in wizard'))

        if not self.aisle_ids:
            raise except_orm(_('Error'), _('Not Aisle configuration defined'))

        camera_obj = self.env['stock.location'].browse(active_id)
        new_loc_ids = []
        pick_zone_obj, store_zone_obj = self._create_camera_zone(camera_obj)
        for item in self[0].aisle_ids:
            list_vals = self._get_locations_vals(item, camera_obj,
                                                 pick_zone_obj,
                                                 store_zone_obj)
            if not list_vals:
                raise except_orm(_('Error'), _('No locations will be created'))
            for vals in list_vals:
                created_loc = self.env['stock.location'].create(vals)
                new_loc_ids.append(created_loc.id)
        # No esta funcionando devolver la vista lista de ubicaciones creadas
        action_obj = self.env.ref('stock.action_location_form')
        action = action_obj.read()[0]
        action['domain'] = str([('id', 'in', new_loc_ids)])
        return action


class aisle_record(models.TransientModel):
    _name = "aisle.record"
    _rec_name = "aisle_num"

    @api.one
    @api.onchange('num_cols', 'num_heights', 'num_subcols', 'pick_heights')
    def _calc_ubications_totals(self):
        """
        Only to show info in the wizard view
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
    my_length = fields.Float('Length', default=1.20, required=True)
    my_width = fields.Float('Width', default=0.8, required=True)
    my_height = fields.Float('Height', default=2.5, required=True)
