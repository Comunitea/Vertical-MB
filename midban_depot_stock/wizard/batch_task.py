# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Kiko Sánchez <kiko@comunitea.com>$
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
from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _
import time
import logging
_logger = logging.getLogger(__name__)


class BatchTasks(models.TransientModel):

    _name = 'batch.task'

    stock_task = fields.Many2one('stock.task','Stock Task')

    @api.multi
    def finish_batch_task_not_force(self):#, force = False):
        return self.finish_batch_task(force = False, context = self._context)

    @api.multi
    def finish_batch_task_force(self):#, force = False):
        return self.finish_batch_task(force = True, context = self._context)

    @api.multi
    def finish_batch_task(self, force = False, context = {}):#, force = False):
        init_t = time.time()
        active_ids = self.env.context['active_ids']
        if active_ids:
            task_ids = self.env['stock.task'].browse(active_ids)
            for task in task_ids:
                if task.state in ['assigned', 'process']:
                    if force and task.wave_id:
                        for wave_report in task.wave_id.wave_report_ids:
                            wave_report.operation_ids.write ({'to_process': True})
                    task.finish_partial_task()
        action_obj = self.env.ref('midban_depot_stock.action_stock_task')
        action = action_obj.read()[0]
        action['domain'] = str([('id', 'in', task_ids._ids)])
        action['context'] = {}
        return action


