# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 COmunitea Servicios Tecnológicos All Rights Reserved
#    $Kiko Sánchez$ <kiko@comunitea.com>
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
from openerp import models, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round


class product_product(models.Model):

    _inherit = "product.product"



    # @api.model
    # def get_ratios(self, unit, supplier_id):
    #     if supplier_id:
    #         supp = self.get_product_supp_record(supplier_id)
    #         kg_un = supp.supp_kg_un or 1.0
    #         un_ca = supp.supp_un_ca or 1.0
    #         ca_ma = supp.supp_ca_ma or 1.0
    #         ma_pa = supp.supp_ma_pa or 1.0
    #     else:
    #         supp = self
    #         kg_un = self.supplier_kg_un or 1.0
    #         un_ca = self.supplier_un_ca or 1.0
    #         ca_ma = self.supplier_ca_ma or 1.0
    #         ma_pa = self.supplier_ma_pa or 1.0
    #
    #
    #     uom = self.env['product.uom'].browse ([(unit)])
    #     res = 1.0
    #     if uom.like_type == 'palets' or uom.like_type == 'mantles':
    #         res = self.get_ratio_logis_to_box(uom.like_type, supplier_id)
    #
    #     res = float_round(res * self._get_unit_ratios(unit, supplier_id),2)
    #     return res


    # @api.model
    # def get_ratio_logis_to_box(self, logis_id, supplier_id):
    #
    #     if supplier_id:
    #         supp = self.get_product_supp_record(supplier_id)
    #         kg_un = supp.supp_kg_un or 1.0
    #         un_ca = supp.supp_un_ca or 1.0
    #         ca_ma = supp.supp_ca_ma or 1.0
    #         ma_pa = supp.supp_ma_pa or 1.0
    #     else:
    #         supp = self
    #         kg_un = self.supplier_kg_un or 1.0
    #         un_ca = self.supplier_un_ca or 1.0
    #         ca_ma = self.supplier_ca_ma or 1.0
    #         ma_pa = self.supplier_ma_pa or 1.0
    #
    #
    #     if logis_id == 'palets':
    #         unit_logis = ca_ma * ma_pa
    #
    #     if logis_id == 'mantles':
    #         unit_logis = ca_ma
    #
    #     return unit_logis



