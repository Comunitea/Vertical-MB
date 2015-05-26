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


if 'old_write' not in dir(models.BaseModel):
    models.BaseModel.old_write = models.BaseModel.write


@api.multi
def write(self, vals):
    model = self.env['ir.model'].search([('model', '=', str(self._model))])
    try:
        field_logger = self.env['logger.config'].search([('name', '=',
                                                          model.id)])
    except:
        return self.old_write(vals)
    if field_logger:
        changes = _("Changed fields:")
        watch_fields = {}
        for field in field_logger.watch_fields:
            """
                Se busca la traduccion manualmente porque utilizando _() no
                funciona correctamente
            """
            translation = self.env['ir.translation'].search(
                [('src', '=', field.field_description),
                 ('lang', '=', self.env.context.get('lang', 'en_US'))])
            watch_fields[field.name] = (translation and translation[0].value or
                                        field.field_description, field.ttype,
                                        field.relation)
        for field in vals.keys():
            if field in watch_fields.keys():
                if watch_fields[field][1] == 'one2many' or \
                        watch_fields[field][1] == 'many2many':
                    change_list = [_('<br/>Field %s changed:') %
                                   _(watch_fields[field][0])]
                    for record in vals[field]:
                        if record[0] == 0:
                            if 'name' in record[2].keys():
                                change_list.append(_('Added %s') %
                                                   record[2]['name'])
                        elif record[0] == 1:
                            pass
                        elif record[0] in (2, 3, 4):
                            recordset = self.env[watch_fields[field][2]].browse(record[1])
                            if record[0] == 4:
                                change_list.append(_('Added %s') %
                                                   recordset.name)
                            else:
                                change_list.append(_('Removed %s') %
                                                   recordset.name)
                        elif record[0] == 5:
                            chage_list.append('Removed all')
                        elif record[0] == 6:
                            for record_id in record[2]:
                                if record_id not in self[field]._ids:
                                    recordset = self.env[watch_fields[field][2]].browse(record_id)
                                    change_list.append(_('Added %s') %
                                                       recordset.name)
                            for record_id in self[field]._ids:
                                if record_id not in record[2]:
                                    recordset = self.env[watch_fields[field][2]].browse(record_id)
                                    change_list.append(_('Removed %s') %
                                                       recordset.name)
                    changes += '<br/>'.join(change_list)
                else:
                    if vals[field] != self[field]:
                        changes += _("<br/>Field %s changed: %s -> %s") % \
                            (watch_fields[field][0], self[field],
                             vals[field])
        if changes and changes != _("Changed fields:"):
            self.message_post(body=changes)
    return self.old_write(vals)

#override write method
models.BaseModel.write = write


class logger_config(models.Model):

    _name = 'logger.config'

    name = fields.Many2one('ir.model', 'Model')
    watch_fields = fields.Many2many(
        'ir.model.fields',
        'logger_model_fields_rel',
        'logger_id',
        'field_id',
        'Watch fields')

    @api.model
    def create(self, vals):
        if vals.get('name'):
            mail_field = self.env['ir.model.fields'].search(
                [('model_id', '=', vals['name']),
                 ('name', '=', 'message_follower_ids')])
            if not mail_field:
                model = self.env['ir.model'].browse(vals['name'])
                raise exceptions.Warning(_('Model error'),
                                         _('The model %s not have messaging')
                                         % model.name)
        return super(logger_config, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('name'):
            mail_field = self.env['ir.model.fields'].search(
                [('model_id', '=', vals['name']),
                 ('name', '=', 'message_follower_ids')])
            if not mail_field:
                model = self.env['ir.model'].browse(vals['name'])
                raise exceptions.Warning(_('Model error'),
                                         _('The model %s not have messaging')
                                         % model.name)
        return super(logger_config, self).write(vals)
