AL exportar traducciones de midban_product,
algunas salen de exportar las del modelo product, ya que son de la vista de
product.supplierinfo, hay que acordarse de meterlas, de momento son estas:

#. module: product
#: view:product.supplierinfo:product.product_supplierinfo_form_view
#: view:product.template:product.product_template_form_view
msgid "Information"
msgstr "Información"

#. module: product
#: view:product.supplierinfo:product.product_supplierinfo_form_view
msgid "Logistic Information"
msgstr "Información logística"

#. module: product
#: view:product.supplierinfo:product.product_supplierinfo_form_view
msgid "Relations units - logistic"
msgstr "Relación unidades - logística"

#. module: product
#: view:product.supplierinfo:product.product_supplierinfo_form_view
msgid "Coefficients and sizes of logistic units"
msgstr "Coeficientes y tamaños de unidades logísticas"

#. module: midban_product
#: field:product.template,sale_euro_weight:0
msgid "Sale Euro Weight"
msgstr "€/Kg venta"

#. module: midban_product
#: field:product.template,buy_euro_weight:0
msgid "Buy Euro Weight"
msgstr "€/Kg compra"

#. module: midban_product
#: help:product.template,sale_euro_weight:0
msgid "Price per gross weight in a sale"
msgstr "Precio por peso bruto en una venta"

#. module: midban_product
#: help:product.template,buy_euro_weight:0
msgid "Price per gross weight in a purchase"
msgstr "Precio por peso bruto en una compra"
