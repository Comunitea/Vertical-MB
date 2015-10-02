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
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class FastReturn(models.TransientModel):

    _name = 'fast.return'

    @api.multi
    def fast_return(self):
        pickings = self.env['stock.picking'].browse(self.env.context['active_ids'])
        picking_ids = pickings.fast_returns()
        if not picking_ids:
            raise except_orm(_('Error!'), _('No return picking created!'))
        data_pool = self.env['ir.model.data']

        #action_id = data_pool.xmlid_to_res_id('stock.action_picking_tree_ready')

        # Return the next view: Show 'done' view
        #
        model_data_ids = data_pool.search([
            ('model', '=', 'ir.ui.view'),
            ('module', '=', 'stock'),
            ('name', '=', 'vpicktree')
        ])
        model_data_form_ids = data_pool.search([
            ('model', '=', 'ir.ui.view'),
            ('module', '=', 'stock'),
            ('name', '=', 'view_picking_form')
        ])

        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        resource_form_id = model_data_form_ids.read(fields=['res_id'])[0]['res_id']

        return {
            'name': _("New return pickings"),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(resource_id, 'tree'),(resource_form_id, 'form')],
            'domain': "[('id','in', ["+','.join(map(str, picking_ids))+"])]",
            'context': self.env.context,
            'target': 'current',
        }

        # if action_id:
        #     action_pool = self.env['ir.actions.act_window']
        #     action = action_pool.read(self.env.cr, self.env.uid, action_id)
        #     action['domain'] = "[('id','in', ["+','.join(map(str, picking_ids))+"])]"
        #     return action
        # return True

