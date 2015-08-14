# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra$ <omar@comunitea.com>
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

import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestProduct(openerp.tests.TransactionCase):

    def setUp(self):
        super(TestProduct, self).setUp()
        self.product = self.registry('product.product')
        self.uom = self.registry('product.uom')
        self.imd = self.registry('ir.model.data')
        self.partner = self.registry('res.partner')
        self.supp_info = self.registry('product.supplierinfo')
        #Test Supplier
        cr, uid = self.cr, self.uid
        supplier_id = self.partner.create(cr, uid, {"name": "Test Supplier",
                                                    "is_company": True,
                                                    "active": True,
                                                    "supplier": True,
                                                    "customer": False})
        self.supplier = self.partner.browse(cr, uid, supplier_id)

    def test_procut_case_1(self):
        """Caja de 10 magnums (unidad es caja de 10)"""
        cr, uid = self.cr, self.uid
        unit_id = self.imd.get_object_reference(cr, uid, 'product',
                                                'product_uom_unit')[1]
        box_id = self.imd.get_object_reference(cr, uid, 'midban_depot_stock',
                                               'product_uom_box')[1]
        prod_id = self.product.create(cr, uid, {"name": "Caja de 10 magnums",
                                                "uom_id": unit_id,
                                                "list_price": 5.0,
                                                "log_unit_id": unit_id,
                                                "unit_use_sale": True,
                                                "log_box_id": box_id,
                                                "un_ca": 6,
                                                "uom_po_id": unit_id,
                                                "standard_price": 3,
                                                "active": True})
        prod = self.product.browse(cr, uid, prod_id)
        self.supp_info.create(cr, uid, {"name": self.supplier.id,
                                        "product_tmpl_id": prod.
                                        product_tmpl_id.id,
                                        "log_unit_id": unit_id,
                                        "unit_use_purchase": True,
                                        "log_box_id": box_id,
                                        "box_use_purchase": True,
                                        "supp_un_ca": 6,
                                        "supp_ca_ma": 20,
                                        "supp_ma_pa": 5})
        self.assertEquals(prod.is_var_coeff, False,
                          "Caja de 10 magnums is not variable.")

        sale_unit_ids = self.uom.search(cr, uid, [],
                                        context={'product_id': prod_id})
        self.assertEquals(set(sale_unit_ids), set([unit_id]),
                          "Caja de 10 magnums only saleable in units.")

        purchase_unit_ids = self.uom.\
            search(cr, uid, [], context={'supp_product_id': prod_id,
                                         'supplier_id': self.supplier.id})
        self.assertEquals(set(purchase_unit_ids), set([unit_id, box_id]),
                          "Caja de 10 magnums only purchaseable in units"
                          " and boxes.")
        # Sales
        res = prod.uom_qty_to_uos_qty(10, unit_id)
        self.assertEquals(res, 10, "10 units of Caja de 10 magnums are "
                                   "10 units in sale.")
        res = prod.uos_qty_to_uom_qty(10, unit_id)
        self.assertEquals(res, 10, "10 units in sale of Caja de 10 magnums "
                                   "are 10 units uom.")
        prices = prod.get_uom_uos_prices(unit_id, custom_price_unit=10.0)
        self.assertEquals(prices, (10.0, 10.0), "10 as unit price for Caja de "
                                                "10 magnums in sale are"
                                                "10 in uos price.")
        prices = prod.get_uom_uos_prices(unit_id, custom_price_udv=15.0)
        self.assertEquals(prices, (15.0, 15.0), "15 as uos price for Caja de "
                                                "10 magnums in sale are"
                                                "15 in price unit.")

        #Purchases
        res = prod.uom_qty_to_uoc_qty(60, box_id, self.supplier.id)
        self.assertEquals(res, 10, "60 unis of Caja de 10 magnums are "
                                   "10 boxes in purchase.")
        supp_log_unit = prod.get_uom_po_logistic_unit(self.supplier.id)
        self.assertEquals(supp_log_unit, "unit", "The uom in purchase must "
                                                  "be unit.")
        conv = prod.get_purchase_unit_conversions(10, box_id, self.supplier.id)
        self.assertEquals(conv[supp_log_unit], 60, "10 boxes in purchase of "
                                                   "Caja de 10 magnums "
                                                   "are 60 units uom.")

    def test_procut_case_2(self):
        """Lomo de ternera 5-6Kg"""
        cr, uid = self.cr, self.uid
        unit_id = self.imd.get_object_reference(cr, uid, 'product',
                                                'product_uom_unit')[1]
        box_id = self.imd.get_object_reference(cr, uid, 'midban_depot_stock',
                                               'product_uom_box')[1]
        kg_id = self.imd.get_object_reference(cr, uid, 'product',
                                              'product_uom_kgm')[1]
        prod_id = self.product.create(cr, uid, {"name":
                                                "Lomo de ternera 5-6Kg",
                                                "uom_id": kg_id,
                                                "list_price": 3.0,
                                                "log_base_id": kg_id,
                                                "base_use_sale": True,
                                                "log_unit_id": unit_id,
                                                "unit_use_sale": True,
                                                "log_box_id": box_id,
                                                "box_use_sale": True,
                                                "kg_un": 5.5,
                                                "var_coeff_un": True,
                                                "un_ca": 4,
                                                "var_coeff_ca": True,
                                                "uom_po_id": kg_id,
                                                "standard_price": 1,
                                                "active": True})
        prod = self.product.browse(cr, uid, prod_id)
        self.supp_info.create(cr, uid, {"name": self.supplier.id,
                                        "product_tmpl_id": prod.
                                        product_tmpl_id.id,
                                        "log_unit_id": unit_id,
                                        "unit_use_purchase": True,
                                        "log_box_id": box_id,
                                        "box_use_purchase": True,
                                        "log_base_id": kg_id,
                                        "base_use_purchase": True,
                                        "supp_kg_un": 5.5,
                                        "var_coeff_un": True,
                                        "supp_un_ca": 4,
                                        "var_coeff_ca": True})
        self.assertEquals(prod.is_var_coeff, True,
                          "Lomo de ternera 5-6Kg is variable.")

        sale_unit_ids = self.uom.search(cr, uid, [],
                                        context={'product_id': prod_id})
        self.assertEquals(set(sale_unit_ids), set([unit_id, box_id, kg_id]),
                          "Lomo de ternera 5-6Kg is saleable in units, boxes"
                          " and kg.")

        purchase_unit_ids = self.uom.\
            search(cr, uid, [], context={'supp_product_id': prod_id,
                                         'supplier_id': self.supplier.id})
        self.assertEquals(set(purchase_unit_ids), set([unit_id, box_id,
                                                       kg_id]),
                          "Lomo de ternera 5-6Kg purchaseable in units, kg"
                          " and boxes.")
        # Sales
        res = prod.uom_qty_to_uos_qty(55, kg_id)
        self.assertEquals(res, 55, "55 kg. of Lomo de ternera 5-6Kg are "
                                   "55 kg. in sale.")
        res = prod.uom_qty_to_uos_qty(55, unit_id)
        self.assertEquals(res, 10, "55 kg. of Lomo de ternera 5-6Kg are "
                                   "approx. 10 units in sale.")
        res = prod.uom_qty_to_uos_qty(44, box_id)
        self.assertEquals(res, 2, "44 kg. of Lomo de ternera 5-6Kg are "
                                   "approx. 2 boxes in sale.")

        res = prod.uos_qty_to_uom_qty(10, kg_id)
        self.assertEquals(res, 10, "10 kg in sale of Lomo de ternera 5-6Kg "
                                   "are 10 kg uom.")
        res = prod.uos_qty_to_uom_qty(10, unit_id)
        self.assertEquals(res, 55, "10 units in sale of Lomo de ternera 5-6Kg "
                                   "are 55 kg uom.")
        res = prod.uos_qty_to_uom_qty(2, box_id)
        self.assertEquals(res, 44, "2 boxes in sale of Lomo de ternera 5-6Kg "
                                   "are 44 kg uom.")

        prices = prod.get_uom_uos_prices(kg_id, custom_price_unit=3)
        self.assertEquals(prices, (3, 3), "3 as unit price for Lomo de "
                                          "ternera 5-6Kg in sale are"
                                          "3 in uos (kg) price.")
        prices = prod.get_uom_uos_prices(unit_id, custom_price_unit=3)
        self.assertEquals(prices, (3, 16.5), "3 as unit price for Lomo de "
                                             "ternera 5-6Kg in sale are"
                                              "16,5 in uos (unit) price.")
        prices = prod.get_uom_uos_prices(unit_id, custom_price_udv=16.5)
        self.assertEquals(prices, (3, 16.5), "16,5 as uos price for Lomo de "
                                             "ternera 5-6Kg in sale are"
                                             "3 in price unit.")

        prices = prod.get_uom_uos_prices(kg_id, custom_price_unit=3)
        self.assertEquals(prices, (3, 3), "3 as unit price for Lomo de "
                                          "ternera 5-6Kg in sale are"
                                          "3 in uos (kg) price.")
        prices = prod.get_uom_uos_prices(box_id, custom_price_unit=3)
        self.assertEquals(prices, (3, 66), "3 as unit price for Lomo de "
                                           "ternera 5-6Kg in sale are"
                                           "66 in uos (box) price.")
        prices = prod.get_uom_uos_prices(unit_id, custom_price_unit=3)
        self.assertEquals(prices, (3, 16.5), "3 as unit price for Lomo de "
                                           "ternera 5-6Kg in sale are"
                                           "16,6 in uos (unit) price.")

        #Purchases
        res = prod.uom_qty_to_uoc_qty(55, kg_id, self.supplier.id)
        self.assertEquals(res, 55, "55 kg. of Lomo de ternera 5-6Kg are "
                                   "55 kg. in purchase.")
        res = prod.uom_qty_to_uoc_qty(44, box_id, self.supplier.id)
        self.assertEquals(res, 2, "44 kg. of Lomo de ternera 5-6Kg are "
                                  "2 boxes in purchase.")
        res = prod.uom_qty_to_uoc_qty(55, unit_id, self.supplier.id)
        self.assertEquals(res, 10, "55 kg. of Lomo de ternera 5-6Kg are "
                                   "10 units in purchase.")
        supp_log_unit = prod.get_uom_po_logistic_unit(self.supplier.id)
        self.assertEquals(supp_log_unit, "base", "The uom in purchase must "
                                                  "be base.")
        conv = prod.get_purchase_unit_conversions(2, box_id, self.supplier.id)
        self.assertEquals(conv[supp_log_unit], 44, "2 boxes in purchase of "
                                                   "Lomo de ternera 5-6Kg "
                                                   "are 44 kg uom.")
        conv = prod.get_purchase_unit_conversions(55, kg_id, self.supplier.id)
        self.assertEquals(conv[supp_log_unit], 55, "55 kg in purchase of "
                                                    "Lomo de ternera 5-6Kg "
                                                    "are 55 kg uom.")
        conv = prod.get_purchase_unit_conversions(10, unit_id, self.supplier.id)
        self.assertEquals(conv[supp_log_unit], 55, "10 units in purchase of "
                                                    "Lomo de ternera 5-6Kg "
                                                    "are 55 kg uom.")

