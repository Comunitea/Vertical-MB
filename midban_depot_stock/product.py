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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import models, api
from openerp import fields as fields2
import logging
_logger = logging.getLogger(__name__)

class product_template(osv.Model):
    """
    Adding field picking location
    """
    _inherit = "product.template"

    def _stock_conservative(self, cr, uid, ids, field_names=None,
                            arg=False, context=None):
        """ Finds the outgoing quantity of product.
        @return: Dictionary of values
        """
        if not field_names:
            field_names = []
        if context is None:
            context = {}
        res = {}
        prod = self.pool.get('product.template')
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        if 'virtual_stock_conservative' in field_names:
            # Virtual stock conservative = real qty - outgoing qty
            for id in ids:
                realqty = prod.browse(cr,
                                      uid,
                                      id,
                                      context=context).qty_available
                outqty = prod.browse(cr,
                                     uid,
                                     id,
                                     context=context).outgoing_qty
                res[id] = realqty - outqty
        return res

    def _is_cross_dock(self, cr, uid, ids, field_names=None,
                       arg=False, context=None):
        """
        Return True if product has marked a route with cross dock check marked,
        """
        res = {}
        for prod in self.browse(cr, uid, ids, context):
            res[prod.id] = False
            for route in prod.route_ids:
                if route.cross_dock:
                    res[prod.id] = True
                    break
        return res

    _columns = {
        'picking_location_id': fields.many2one('stock.location',
                                               'Location Picking'),
        'volume': fields.float('Volume', help="The volume in m3.",
                               digits_compute=dp.get_precision
                               ('Product Volume')),
        'virtual_stock_conservative': fields.function(_stock_conservative,
                                                      type='float',
                                                      string='Virtual \
                                                              Stock \
                                                              Conservative',
                                                      readonly=True),
        'is_cross_dock': fields.function(_is_cross_dock,
                                         type='boolean',
                                         string='Cros Dock \
                                         Product',
                                         readonly=True),
        'limit_time': fields.integer('min useful time',
                                     help='Minimum days of expiration. \
                                     If you enter a product in stock with \
                                     lower incidence expiration is created.'),

    }
    # Se anula para poner zona
    _sql_constraints = [
        ('location_id_uniq', 'Check(1=1)',
         _("Field Location picking is already setted"))
    ]

    def get_locations_by_zone(self, cr, uid, product_id, zone, context=None):
        """
        Get al the locatios child of storage location for the product camera.
        The product must have a picking_location, in other case raise an error.
        """
        if context is None:
            context = {}
        t_loc = self.pool.get('stock.location')
        storage_loc_ids = []
        if product_id:
            product = self.browse(cr, uid, product_id, context)
            if not product.picking_location_id:
                raise osv.except_osv(_('Error!'), _('Not picking location.'))
            if zone not in ['picking', 'storage']:
                raise osv.except_osv(_('Error!'), _('Zone not exist.'))
            pick_loc_id = product.picking_location_id.id
            storage_loc_ids = t_loc.get_locations_by_zone(cr, uid,
                                                          pick_loc_id,
                                                          zone,
                                                          context=context)
        return storage_loc_ids

    def copy(self, cr, uid, id, default=None, context=None):
        default = {} if default is None else default.copy()
        default.update({
            'picking_location_id': False
        })
        return super(product_template, self).copy(cr, uid, id, default=default,
                                                  context=context)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    log_units_available = fields2.Float("Logistic units quantity",
                                        readonly=True,
                                        compute='_get_log_units_available',
                                        help="Shows stock in the logistic \
                                              unit defined as units aprox.")

    @api.one
    @api.depends('var_coeff_un', 'var_coeff_ca', 'kg_un')
    def _get_log_units_available(self):
        """
        Calc stock in logistic units defined as units
        """
        _logger.debug("CMNT _get_log_units_available")
        self.log_units_available = 0.0
        if self.var_coeff_un or self.var_coeff_ca:
            prod_ids = self.env['product.product'].search([('product_tmpl_id',
                                                            '=',
                                                            self.id)])
            if prod_ids:
                prod = prod_ids[0]
                #conv = prod.get_unit_conversions(self.virtual_available,
                #                                 self.uom_id.id)
                #self.log_units_available = conv['unit']

                #NOTA. No tendrái porqueñ ser a este unidad ,Creo que trelametne deberáismo poder ver si queremos ver
                #segunda unidad el stock, cual es esta unidad en al que queremos verlo....
                if self.log_unit_id:
                    self.log_units_available = prod.uom_qty_to_uos_qty(prod.virtual_available, self.log_unit_id.id)
                else:
                    self.log_units_available = -1.0


class ProductUom(models.Model):

    _inherit = 'product.uom'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """ Overwrite in order to search only allowed products for a product
            if product_id is in context."""
        if context is None:
            context = {}
        if context.get('supp_product_id', False) and context.get('supplier_id',
                                                                 False):
            t_prod = self.pool.get('product.product')
            prod = t_prod.browse(cr, uid, context['supp_product_id'], context)
            prod_udc_ids = prod.get_purchase_unit_ids(context['supplier_id'])
            # Because sometimes args = [category = False]
            args = [['id', 'in', prod_udc_ids]]
        elif context.get('product_id', False):
            t_prod = self.pool.get('product.product')
            prod = t_prod.browse(cr, uid, context['product_id'], context)
            product_udv_ids = prod.get_sale_unit_ids()
            # Because sometimes args = [category = False]
            args = [['id', 'in', product_udv_ids]]
        return super(ProductUom, self).search(cr, uid, args,
                                              offset=offset,
                                              limit=limit,
                                              order=order,
                                              context=context,
                                              count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        res = super(ProductUom, self).name_search(name, args=args,
                                                  operator=operator,
                                                  limit=limit)
        if self._context.get('supp_product_id', False) and \
                self._context.get('supplier_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            res = recs.name_get()
        elif self._context.get('product_id', False):
            args = args or []
            recs = self.browse()
            recs = self.search(args)
            res = recs.name_get()

        return res
