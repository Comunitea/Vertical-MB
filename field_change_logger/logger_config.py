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
from openerp.addons.base.ir import ir_model

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
        for watch_field in field_logger.watch_fields:
            """
                Se busca la traduccion manualmente porque utilizando _() no
                funciona correctamente
            """
            field = watch_field.log_field
            translation = self.env['ir.translation'].search(
                [('src', '=', field.field_description),
                 ('lang', '=', self.env.context.get('lang', 'en_US'))])
            watch_fields[field.name] = (translation and translation[0].value or
                                        field.field_description, field.ttype,
                                        field.relation,
                                        watch_field.use_field.name)
        for field in vals.keys():
            if field in watch_fields.keys():
                model = watch_fields[field][2]
                show_field = watch_fields[field][3]
                if watch_fields[field][1] == 'one2many' or \
                        watch_fields[field][1] == 'many2many':
                    change_list = [_('<br/>Field %s changed:') %
                                   _(watch_fields[field][0])]
                    for record in vals[field]:
                        if record[0] == 0:
                            if show_field in record[2].keys():
                                change_list.append(_('Added %s') %
                                                   record[2][show_field])
                        elif record[0] == 1:
                            pass
                        elif record[0] in (2, 3, 4):
                            recordset = self.env[model].browse(record[1])
                            if record[0] == 4:
                                change_list.append(_('Added %s') %
                                                   recordset[show_field])
                            else:
                                change_list.append(_('Removed %s') %
                                                   recordset[show_field])
                        elif record[0] == 5:
                            chage_list.append('Removed all')
                        elif record[0] == 6:
                            for record_id in record[2]:
                                if record_id not in self[field]._ids:
                                    recordset = self.env[model].browse(
                                        record_id)
                                    change_list.append(_('Added %s') %
                                                       recordset[show_field])
                            for record_id in self[field]._ids:
                                if record_id not in record[2]:
                                    recordset = self.env[model].browse(
                                        record_id)
                                    change_list.append(_('Removed %s') %
                                                       recordset[show_field])
                    changes += '<br/>'.join(change_list)
                elif watch_fields[field][1] == 'many2one':
                    if not vals[field]:
                        changes += _("<br/>Field %s removed: %s") % \
                            (watch_fields[field][0], self[field][show_field])
                    elif not self[field]:
                        new_obj = self.env[model].browse(vals[field])
                        changes += _("<br/>Field %s added: %s") % \
                            (watch_fields[field][0], new_obj[show_field])
                    elif vals[field] != self[field].id:
                        new_obj = self.env[model].browse(vals[field])
                        changes += _("<br/>Field %s changed: %s -> %s") % \
                            (watch_fields[field][0], self[field][show_field],
                             new_obj[show_field])
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
    watch_fields = fields.One2many('logger.config.field', 'logger',
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


class loggerConfigField(models.Model):

    _name = 'logger.config.field'

    log_field = fields.Many2one('ir.model.fields', 'Field', required=True)
    field_type = fields.Selection(ir_model._get_fields_type, 'Field type',
                                  related='log_field.ttype', readonly=True)
    relation_name = fields.Char('Relation', related='log_field.relation',
                                readonly=True)
    use_field = fields.Many2one('ir.model.fields', 'Show field')
    logger = fields.Many2one('logger.config', 'Logger')
