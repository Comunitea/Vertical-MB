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
from openerp import pooler


class issue_generator(object):
    """ This class could be imported in order to create issues with a variable
        number of arguments
    """

    def create_issue(self, cr, uid, ids, res_model, res_ids, code, **kw):
        """ Allows create issues with a variable number of arguments.
            you can pass the following arguments:
            MANDATORY ARGUMENTS:
            **res_model --> 'sale.order','purchase.order' or'stock.picking'
            **res_id --> id of object related with issue
            **code --> Reason code, issue type will be seted with reason type
            OPTIONAL ARGUMENTS:
            **flow --> string 'model,id', associed flow of incidence
            **origin--> char field with origin point of issue
            **edi_message -> selection ('desadv2,recadv')
            **type_id --> id of issue.type (maybe map it  here?)
            **reason_id --> id of issue.reasson (maybe map it  here?)
            **affected_fields --> char field with affected fields
            **affected_partner_id --> id of affected partner of issue
            **caused_partner_id --> id of caused partenr of issue
            **solution --> char field explaining how issue were solved
            **product_ids --> list of dicts containing values of product.info
                              obj. ej [{'product_id':2,
                                        'uom_id':3,
                                        'product_qty':20},other dic,...]
            Created issues are marked as automatic,
        """
        pool = pooler.get_pool(cr.dbname)
        create_id = False
        for res_id in res_ids:
            ref = '%s,%s' % (res_model, res_id)
            reason_id = pool.get('issue.reason').search(cr,
                                                        uid,
                                                        [('code', '=', code)])
            if not reason_id:
                raise Exception("Code of reason_id does not exist")
            reason_obj = pool.get("issue.reason").browse(cr,
                                                         uid,
                                                         reason_id[0])
            type_id = reason_obj.type_id and reason_obj.type_id.id or False
            product_info_ids = []
            if 'product_ids' in kw:
                for dic in kw['product_ids']:
                    if not dic.get('reason_id'):
                        dic['reason_id'] = reason_id[0]
                    product_info_ids.append((0, 0, dic))
            kw.update({'res_model': res_model,
                       'res_id': res_id,
                       'object': ref,
                       'reason_id': reason_id[0],
                       'type_id': type_id,
                       'automatic': True,
                       'product_ids': product_info_ids})
            create_id = pool.get('issue').create(cr, uid, kw)
        return create_id
