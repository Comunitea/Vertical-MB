# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Santi Argüeso <santi@comunitea.com>$
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
from openerp.osv import fields, osv

class product_pricelist(osv.Model):
    _inherit = 'product.pricelist'
    _columns = {
        'fallback_pricelist_id': fields.many2one('product.pricelist', 'Fallback pricelist'),

    }
    def _price_rule_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner,
                         context=None):
        res = super(product_pricelist, self)._price_rule_get_multi(cr, uid,
                                                              pricelist,
                                                              products_by_qty_by_partner,
                                                            context = context)
        print "RES!!!!!!"
        print res
        results = {}
        for product_id,item in res.items():
            if item[0] == 0 and pricelist.fallback_pricelist_id:
                print "Precio 0"
                print product_id
                for terna in products_by_qty_by_partner:
                    print terna
                    if terna[0] == product_id:
                        new_res = self._price_get_multi(cr, uid, pricelist.fallback_pricelist_id,
                                              [terna], context=context)[0]
                        print "new_res"
                        print new_res
                        res[product_id] = new_res[product_id]
        print res
        return res