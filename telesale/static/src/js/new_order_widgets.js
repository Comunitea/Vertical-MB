function openerp_ts_new_order_widgets(instance, module){ //module is instance.point_of_sale
    var QWeb = instance.web.qweb,
    _t = instance.web._t;
    var round_pr = instance.web.round_precision
    var my_round = function(number, decimals){
        var n = number || 0;
        if (typeof n === "string"){
            n = n * 1;
        }
        return n.toFixed(decimals) * 1
    };

    // Buttons of differents order actuing like pages of orders
    module.OrderButtonWidget = module.TsBaseWidget.extend({
        template:'Order-Button-Widget',
        init: function(parent, options) {

            this._super(parent,options);
            var self = this;
            this.order = options.order;
            this.bo_id = this.ts_model.get('bo_id');
            this.order.bind('destroy',function(){ self.destroy(); });
            this.ts_model.bind('change:selectedOrder', _.bind( function(ts_model) {

               self.selectedOrder = ts_model.get('selectedOrder');
               /* self.selectedOrder.unbind('change:partner');*/ //comentado para que no destruya el bind de product catalog
                self.selectedOrder.bind('change:partner', function(){ self.renderElement(); });
                if (self.order === self.selectedOrder) {
                    self.setButtonSelected();
                }
            }, this));
        },
        renderElement:function(){
            this._super();
            this.$('button.select-order').off('click').click(_.bind(this.selectOrder, this));
            this.$('button.close-order').off('click').click(_.bind(this.closeOrder, this));
            if (this.order === this.selectedOrder) {
                    this.setButtonSelected();
                }
        },
        selectOrder: function(event) {
            this.ts_model.set({
                selectedOrder: this.order
            });
        },
        setButtonSelected: function() {

            /*TODO NO SE PONE EL COLOR BIEN, YA QUE COJE UNA LISTA Y NO EL BOTON*/
            var identify = 'button#' + this.bo_id
            $('.select-order').removeClass('selected-order');
            $(identify).addClass('selected-order');
        },
        closeOrder: function(event) {
            this.order.destroy();
        },
    });

    module.DataOrderWidget = module.TsBaseWidget.extend({
        template:'Data-Order-Widget',
        init: function(parent, options) {
            this._super(parent,options);
            this.ts_model.bind('change:selectedOrder', this.change_selected_order, this);
            this.order_model = this.ts_model.get('selectedOrder');
        },
        change_selected_order: function() {
            this.renderElement();
            this.$('#partner').focus();
        },
        renderElement: function () {
            var self = this;
            this.order_model = this.ts_model.get('selectedOrder');
            this._super();
            this.$('#partner_code').blur(_.bind(this.set_value, this, 'partner_code'))
            this.$('#partner').blur(_.bind(this.set_value, this, 'partner'))
            this.$('#date_invoice').blur(_.bind(this.set_value, this, 'date_invoice'))
            this.$('#date_order').blur(_.bind(this.set_value, this, 'date_order'))
            this.$('#date_planned').blur(_.bind(this.set_value, this, 'date_planned'))
            this.$('#coment').blur(_.bind(this.set_value, this, 'coment'))
            this.$('#customer_comment').blur(_.bind(this.set_value, this, 'customer_comment'))
            this.$('#supplier').blur(_.bind(this.set_value, this, 'supplier'))

            //autocomplete products and units from array of names
            this.$('#partner_code').autocomplete({
                source: this.ts_model.get('customer_codes'),
            });
            this.$('#partner').autocomplete({
                source: this.ts_model.get('customer_names'),
            });
            this.$('#supplier').autocomplete({
                source: this.ts_model.get('supplier_names'),
            });

        },
        set_value: function(key) {
            var value = this.$('#'+key).val();
            this.order_model.set(key, value);
            this.perform_onchange(key, value);
        },
        check_partner_routes: function(partner_id) {
            self = this
            var model = new instance.web.Model('res.partner');
            model.call("any_detail_founded",[partner_id])  //TODO revisar:devuelve ids que no estan activos (proceso de baja)
            // .then(function(result){
            //     if (!result){
            //         alert(_t("Customer has no assigned any delivery route"));
            //         self.order_model.set('partner', "");
            //         self.order_model.set('partner_code', "");
            //         self.refresh();
            //     }
            // });
        },
        get_supplier_names: function(partner_obj) {
            self = this
            if (partner_obj.supplier_ids) {
              var supplier_names = [];
                for (var i = 0, len = partner_obj.supplier_ids.length; i < len; i++){
                var key = partner_obj.supplier_ids[i]
                if(self.ts_model.db.suppliers_name_id[key]){
                  supplier_names.push(self.ts_model.db.suppliers_name_id[key])
                }
              }
              self.ts_model.set('supplier_names', supplier_names)
          }
        },
        perform_onchange: function(key, value) {
            if (!value) {return;}
            if (key == "partner_code" || key == "partner"){
                partner_id = (key == "partner_code") ? this.ts_model.db.partner_ref_id[value] : this.ts_model.db.partner_name_id[value];
                if (!partner_id){
                    var alert_msg = (key == "partner_code") ? _t("Customer code '" + value + "' does not exist") : _t("Customer name '" + value + "' does not exist");
                    alert(alert_msg);
                    this.order_model.set('partner', "");
                    this.order_model.set('partner_code', "");
                    this.refresh();
                }
                else{
                    partner_obj = this.ts_model.db.get_partner_by_id(partner_id);
                    var cus_name = partner_obj.comercial || partner_obj.name
                    this.order_model.set('partner', cus_name);
                    this.order_model.set('partner_code', partner_obj.ref ? partner_obj.ref : "");
                    this.order_model.set('customer_comment', partner_obj.comment);
                    this.order_model.set('limit_credit', my_round(partner_obj.credit_limit,2));
                    this.order_model.set('customer_debt', my_round(partner_obj.credit,2));
                    contact_obj = this.ts_model.db.get_partner_contact(partner_id); //If no contacts return itself
                    this.order_model.set('comercial', partner_obj.user_id ? partner_obj.user_id[1] : "");
                    this.order_model.set('contact_name', contact_obj.name);
                    this.check_partner_routes(partner_id);

                    if(this.order_model.get('orderLines').length == 0){
                        $('.add-line-button').click()
                    }
                    else{
                        if (key == "partner") {
                          this.$('#partner_code').focus();
                        }
                        else {
                          this.$('#date_invoice').focus();
                        }
                    }
                    this.refresh();
                    $('#ult-button').click();
                }
            }
            if (key == "date_invoice"){
              this.$('#date_planed').focus();
            }
            if (key == "date_planed"){
              this.$('#date_order').focus();
            }
            if (key == "date_order"){
              this.$('#partner').focus();
            }
        },
        refresh: function(){
            this.renderElement();
        },
    });

// ***********************************************************************************************************************************
// ***********************************************************************************************************************************
    module.OrderlineWidget = module.TsBaseWidget.extend({
        template: 'Order-line-Widget',
        init: function(parent, options) {
            this._super(parent,options);
            this.order_widget = parent
            this.model = options.model;
            this.order = options.order;
            this.price_and_min = false;

            this.model.bind('change_line', this.refresh, this); //#TODO entra demasiadas veces por la parte esta
        },
        click_handler: function() {
            // debugger;
            this.order.selectLine(this.model);
            this.trigger('order_line_selected');
        },
        control_arrow_keys: function(){
          var self=this;
            this.$('.col-product_uos_qty').keydown(function(event){
              // debugger;
              var keyCode = event.keyCode || event.which;
              if (keyCode == 40 || keyCode == 38) {  // KEY DOWWN (40) up (30)
                var selected_line = self.order.selected_orderline;
                if (selected_line){
                    var n_line = selected_line.get('n_line');
                    var idx =(keyCode == 40) ? n_line + 1 : n_line - 1;
                    var next_line = self.order_widget.orderlinewidgets[idx - 1]
                    if (next_line) {

                      self.order.selectLine(next_line.model);
                      next_line.$el.find('.col-product_uos_qty').focus();
                    }
                }
              }
            });
        },
        renderElement: function() {
            var self=this;
            this._super();
            this.$el.unbind()
            this.$el.click(_.bind(this.click_handler, this));
            if(this.model.is_selected()){
                this.$el.addClass('selected');
            }
            // Si el campo se rellena con autocomplete se debe usar blur
            this.$('.col-code').blur(_.bind(this.set_value, this, 'code'));
            this.$('.col-product').blur(_.bind(this.set_value, this, 'product'));
            this.$('.col-product_uos_qty').change(_.bind(this.set_value, this, 'product_uos_qty'));
            this.$('.col-product_uos').blur(_.bind(this.set_value, this, 'product_uos'));
            this.$('.col-price_udv').change(_.bind(this.set_value, this, 'price_udv'));
            this.$('.col-qty').change(_.bind(this.set_value, this, 'qty'));
            this.$('.col-unit').blur(_.bind(this.set_value, this, 'unit'));
            this.$('.col-qnote').blur(_.bind(this.set_value, this, 'qnote'));
            this.$('.col-qty').change(_.bind(this.set_value, this, 'qty'));
            this.$('.col-pvp').change(_.bind(this.set_value, this, 'pvp'));
            this.$('.col-discount').focusout(_.bind(this.set_value, this, 'discount'));
            this.$('.col-total').change(_.bind(this.set_value, this, 'total'));
            this.$('.col-detail').change(_.bind(this.set_value, this, 'detail'));

            // Mapeo de teclas para moverse por la tabla con las flechas
            this.control_arrow_keys()
            // Creamos nueva linea al tabular la última columna de descuento
            if(this.model.get('product')){
                var uos = [];
                product_id = this.ts_model.db.product_name_id[this.model.get('product')]
                product_obj = this.ts_model.db.product_by_id[product_id]
                if(product_obj.base_use_sale){
                    uos.push(product_obj.log_base_id[1]);
                }
                if(product_obj.unit_use_sale){
                    uos.push(product_obj.log_unit_id[1]);
                }
                if(product_obj.box_use_sale){
                    uos.push(product_obj.log_box_id[1]);
                }
                self.$('.col-product_uos').autocomplete({
                    source: uos
                });
            }
           //autocomplete products and units from array of names
            var products_ref = this.ts_model.get('products_codes')
            this.$('.col-code').autocomplete({
                source: products_ref,
            });
            var product_names = this.ts_model.get('products_names')
            this.$('.col-product').autocomplete({
                source: product_names,
            });
            /*this.$('.col-unit').autocomplete({
                source:this.ts_model.get('units_names')
            });*/
            this.$('.col-qnote').autocomplete({
                source:this.ts_model.get('qnotes_names')
            });
        },
        set_value: function(key) {
            var value = this.$('.col-'+key).val();
            var set=true;
            if (key == 'qty' || key == 'pvp' || key == 'total' || key == 'discount' ){
                if (isNaN(value)){
                    this.$('.col-'+key).val(this.model.get(key));
                    alert(_t(value + " is not a valid number"));
                    set=false;
                }
                else
                    value = my_round(value,2);
            }
            if (set){
                // if ( this.model.get(key) != value ){
                    this.model.set(key, value);
                    this.perform_onchange(key);
                // }
            }
        },
        update_stock_product: function(product_id){
            var self=this;
            var domain = [['id', '=', product_id]]
            var loaded = self.ts_model.fetch('product.product',
                                            ['name','product_class','list_price','cmc','default_code','uom_id', 'log_base_id', 'box_discount', 'log_unit_id', 'log_box_id', 'base_use_sale', 'unit_use_sale', 'box_use_sale','virtual_stock_conservative','taxes_id', 'weight', 'kg_un', 'un_ca', 'ca_ma', 'ma_pa', 'product_tmpl_id','products_substitute_ids'],
                                            domain
                                            )
                .then(function(products){
                    self.ts_model.db.add_products(products);
                })
            return loaded
        },
        call_product_id_change: function(product_id){
            var self = this;

            $.when( self.update_stock_product(product_id) )
                        .done(function(){
                            var customer_id = self.ts_model.db.partner_name_id[self.order.get('partner')];
                            var kwargs = {context: new instance.web.CompoundContext({}),partner_id: customer_id}
                            var pricelist_id = (self.ts_model.db.get_partner_by_id(customer_id)).property_product_pricelist;
                            var model = new instance.web.Model("sale.order.line");
                            model.call("product_id_change_with_wh",[[],pricelist_id,product_id],kwargs)
                            .then(function(result){
                                var product_obj = self.ts_model.db.get_product_by_id(product_id);
                                var uom_obj = self.ts_model.db.get_unit_by_id(product_obj.uom_id[0])
                                self.model.set('fresh_price', my_round(result.value.last_price_fresh || 0,2));
                                self.model.set('code', product_obj.default_code || "");
                                self.model.set('product', product_obj.name || "");
                                self.model.set('taxes_ids', result.value.tax_id || []); //TODO poner impuestos de producto o vacio
                                self.model.set('unit', self.model.ts_model.db.unit_by_id[result.value.product_uom].name);
                                self.model.set('product_uos', (result.value.product_uos) ? self.model.ts_model.db.unit_by_id[result.value.product_uos].name : '');
                                self.model.set('qty', 0);
                                self.model.set('discount', 0);
                                self.model.set('weight', my_round(product_obj.weight || 0,2));
                                if (!result.value.price_unit || result.value.price_unit == 'warn') {
                                    result.value.price_unit = 0;
                                }
                                self.model.set('pvp_ref', my_round( (result.value.price_unit != 0 && product_obj.product_class == "normal") ? result.value.price_unit : 0,2 ));
                                self.model.set('pvp', my_round( (product_obj.product_class == "normal") ? (result.value.price_unit || 0) : (result.value.last_price_fresh || 0), 2));
                                self.model.set('margin', my_round( (result.value.price_unit != 0 && product_obj.product_class == "normal") ? ( (result.value.price_unit - product_obj.cmc) / result.value.price_unit) : 0 , 2));

                                // COMENTADO PARA QUE NO SAQUE EL AVISO SIEMPRE
                                // if ( (1 > product_obj.virtual_stock_conservative) && (product_obj.product_class == "normal")){
                                //     alert(_t("You want sale 1 " + " " + product_obj.uom_id[1] + " but only " +  product_obj.virtual_stock_conservative + " available."))
                                //     var new_qty = (product_obj.virtual_stock_conservative < 0) ? 0.0 : product_obj.virtual_stock_conservative
                                //     self.model.set('qty', new_qty);
                                //     self.refresh();
                                // }

                                self.inicialize_unit_values()
                                var subtotal = self.model.get('pvp') * self.model.get('qty') * (1 - self.model.get('discount') / 100.0)
                                self.model.set('total', my_round(subtotal || 0,2));
                                self.refresh();
                                self.$('.col-product_uos_qty').focus()
                                self.$('.col-product_uos_qty').select()

                            });
                        })
                        .fail(function(){
                            alert(_t("NOT WORKING"));
                        })
        },
        inicialize_unit_values: function(){
            var prod_name = this.model.get('product')
            var uos_name = this.model.get('product_uos')
            this.model.set('product_uos_qty', 1)
            var uos_qty = 1
            var price_unit = this.model.get('pvp')
            conv = this.getUnitConversions(prod_name, uos_qty, uos_name)
            log_unit = this.getUomLogisticUnit(prod_name)
            this.model.set('qty', my_round(conv[log_unit], 2));
            var product_id = this.ts_model.db.product_name_id[prod_name];
            var product_obj = this.ts_model.db.get_product_by_id(product_id);
            if(uos_name == product_obj.log_box_id[1]){
                this.model.set('discount', my_round(product_obj.box_discount, 2))
            }
            else{
                this.model.set('discount', my_round(0.00, 2))
            }
            uos_pu = this.getUomUosPrices(prod_name, uos_name,  price_unit)
            this.model.set('price_udv', my_round(uos_pu, 2))
        },
        // Funciones relacionadas con el producto necesarias para los calculos de unidades
        getUnitConversions: function(product_name, qty_uos, uos_name){
            var product_id = this.ts_model.db.product_name_id[product_name];
            var product_obj = this.ts_model.db.get_product_by_id(product_id);
            var uos_id = this.ts_model.db.unit_name_id[uos_name];
            res = {'base': 0.0,
                   'unit': 0.0,
                   'box': 0.0}
            if(uos_id == product_obj.log_base_id[0]){
                res['base'] = qty_uos
                res['unit'] = my_round(res['base'] / product_obj.kg_un, 2)
                res['box'] = my_round(res['unit'] / product_obj.un_ca, 2)
            }
            else if(uos_id == product_obj.log_unit_id[0]){
                res['unit'] = qty_uos
                res['box'] = my_round(res['unit'] / product_obj.un_ca, 2)
                res['base'] = my_round(res['unit'] * product_obj.kg_un, 2)
            }
            else if(uos_id == product_obj.log_box_id[0]){
                res['box'] = qty_uos
                res['unit'] = my_round(res['box'] * product_obj.un_ca, 2)
                res['base'] = my_round(res['unit'] * product_obj.kg_un, 2)
            }
            return res
        },
        getUomLogisticUnit: function(product_name){
            var product_id = this.ts_model.db.product_name_id[product_name];
            var product_obj = this.ts_model.db.get_product_by_id(product_id);
            if(product_obj.uom_id[0] == product_obj.log_base_id[0]){
                return 'base'
            }
            else if(product_obj.uom_id[0] == product_obj.log_unit_id[0]){
                return 'unit'
            }
            else if(product_obj.uom_id[0] == product_obj.log_box_id[0]){
                return 'box'
            }
        },

        getUomUosPrices: function(product_name, uos_name, custom_price_unit, custom_price_udv){
            var product_id = this.ts_model.db.product_name_id[product_name];
            var product_obj = this.ts_model.db.get_product_by_id(product_id);
            var uos_id = this.ts_model.db.unit_name_id[uos_name];
            custom_price_unit = typeof custom_price_unit !== 'undefined' ? custom_price_unit : 0.0;
            custom_price_udv = typeof custom_price_udv !== 'undefined' ? custom_price_udv : 0.0;
            var price_unit = 0.0
            if(custom_price_udv){
                price_udv = custom_price_udv;
                log_unit = this.getUomLogisticUnit(product_name);
                if(uos_id == product_obj.log_base_id[0]){
                    if(log_unit == 'base'){
                        price_unit = price_udv;
                    }
                    if(log_unit == 'unit'){
                        price_unit = price_udv * product_obj.kg_un;
                    }
                    if(log_unit =order= 'box'){
                        price_unit = price_udv * product_obj.kg_un * product_obj.un_ca;
                    }
                    price_unit = price_unit
                }
                else if(uos_id == product_obj.log_unit_id[0]){
                    if(log_unit == 'base'){
                        price_unit = my_round(price_udv / product_obj.kg_un, 2);
                    }
                    if(log_unit == 'unit'){
                        price_unit = price_udv;
                    }
                    if(log_unit == 'box'){
                        price_unit = price_udv * product_obj.un_ca;
                    }
                }
                else if(uos_id == product_obj.log_box_id[0]){
                    if(log_unit == 'base'){
                        price_unit =  my_round(price_udv / (product_obj.kg_un * product_obj.un_ca), 2);
                    }
                    if(log_unit == 'unit'){
                        price_unit = my_round(price_udv / product_obj.un_ca, 2);
                    }
                    if(log_unit == 'box'){
                        price_unit = price_udv;
                    }
                }
                return price_unit;
            }
            else{
                var price_unit = custom_price_unit != 0.0 ? custom_price_unit : product_obj.list_price;
                var price_udv = 0.0;
                log_unit = this.getUomLogisticUnit(product_name);
                if (uos_id == product_obj.log_base_id[0]){
                    if(log_unit == 'base'){
                        price_udv = price_unit;
                    }
                    if(log_unit == 'unit'){
                        price_udv = price_unit * product_obj.kg_un;
                    }
                    if(log_unit == 'box'){
                        price_udv = price_unit * product_obj.kg_un * product_obj.un_ca;
                    }
                }
                else if(uos_id == product_obj.log_unit_id[0]){
                    if(log_unit == 'base'){
                        price_udv = my_round(price_unit * product_obj.kg_un, 2);
                    }
                    if(log_unit == 'unit'){
                        price_udv = price_unit;
                    }
                    if(log_unit == 'box'){
                        price_udv = price_unit / product_obj.un_ca;
                    }
                }

                else if(uos_id == product_obj.log_box_id[0]){
                    if(log_unit == 'base'){
                        price_udv = my_round(price_unit * product_obj.kg_un * product_obj.un_ca, 2);
                    }
                    if(log_unit == 'unit'){
                        price_udv = my_round(price_unit * product_obj.un_ca, 2);
                    }
                    if(log_unit == 'box'){
                        price_udv = price_unit;
                    }
                }
                return price_udv;
            }
        },

        perform_onchange: function(key) {
            var self=this;
            var value = this.$('.col-'+key).val();
            if (!value) {return;}

            switch (key) {
                case "code":
                    // comprobar que clave está en el array
                    var product_id = this.ts_model.db.product_code_id[value];
                    if (!product_id){
                        alert(_t("Product code '" + value + "' does not exist"));
                        this.model.set('code', "");
                        this.model.set('product', "");
                        this.refresh();
                        break;
                    }
                    this.call_product_id_change(product_id);

                    break;
                case "product":
                    // comprobar que clave está en el array
                    var self = this;
                    product_id = this.ts_model.db.product_name_id[value];
                    if (!product_id){
                        alert(_t("Product name '" + value + "' does not exist"));
                        this.model.set('code', "");
                        this.model.set('product', "");
                        this.refresh();
                        break;
                    }
                    this.call_product_id_change(product_id);
                    break;

                // case "qty":
                //     var prod_name = this.$('.col-product').val();
                //     var product_id = this.ts_model.db.product_name_id[prod_name];
                //     if (!product_id){
                //         alert(_t("Product name '" + prod_name + "' does not exist"));
                //         this.model.set('qty', "1");
                //         this.refresh();
                //         break;
                //     }
                //     var uom_name = this.$('.col-unit').val();
                //     var uom_id = this.ts_model.db.unit_name_id[uom_name];
                //     if (!uom_id){
                //         alert(_t("Unit of measure '" + uom_name + "' does not exist"));
                //         this.model.set('qty', 1);
                //         this.refresh();
                //         break;
                //     }
                //     var product_obj = this.ts_model.db.get_product_by_id(product_id);
                //     if ( (value > product_obj.virtual_stock_conservative) && (product_obj.product_class == "normal")){
                //         alert(_t("You want sale " + value + " " + uom_name + " but only " +  product_obj.virtual_stock_conservative + " available."))
                //         var new_qty = (product_obj.virtual_stock_conservative < 0) ? 0.0 : product_obj.virtual_stock_conservative
                //         this.model.set('qty', new_qty);
                //         this.refresh();
                //         break;
                //     }
                //
                //     //change weight
                //     var weight =  this.model.get('weight')
                //     this.model.set('weight', my_round(value * weight,2));
                //     this.refresh();
                //     break;

                case "product_uos_qty":
                    var prod_name = this.$('.col-product').val();
                    var uos_name = this.$('.col-product_uos').val();
                    conv = this.getUnitConversions(prod_name, value, uos_name)
                    log_unit = this.getUomLogisticUnit(prod_name)
                    this.model.set('product_uos_qty', my_round(value, 2));
                    this.model.set('qty', my_round(conv[log_unit], 2));
                    // Se calculan las cajas
                    var boxes = 0.0
                    var product_id = this.ts_model.db.product_name_id[prod_name];
                    var product_obj = this.ts_model.db.get_product_by_id(product_id);
                    var uos_id = this.ts_model.db.unit_name_id[uos_name];
                    if(uos_id == product_obj.log_base_id[0]){
                        boxes = (value / product_obj.kg_un) / product_obj.un_ca
                    }
                    else if(uos_id == product_obj.log_unit_id[0]){
                        boxes = value / product_obj.un_ca
                    }
                    else if(uos_id == product_obj.log_box_id[0]){
                        boxes = value
                    }
                    this.model.set('boxes', my_round(boxes, 2));
                    this.refresh();
                    break;

                case "product_uos":
                    var prod_name = this.$('.col-product').val();
                    var uos_name = value;
                    var uos_qty = this.$('.col-product_uos_qty').val();
                    var price_unit = this.$('.col-pvp').val();
                    conv = this.getUnitConversions(prod_name, uos_qty, uos_name)
                    log_unit = this.getUomLogisticUnit(prod_name)
                    this.model.set('qty', my_round(conv[log_unit], 2));
                    this.model.set('product_uos', value);
                    var product_id = this.ts_model.db.product_name_id[prod_name];
                    var product_obj = this.ts_model.db.get_product_by_id(product_id);
                    if(uos_name == product_obj.log_box_id[1]){
                        this.model.set('discount', my_round(product_obj.box_discount, 2))
                    }
                    else{
                        this.model.set('discount', my_round(0.00, 2))
                    }
                    uos_pu = this.getUomUosPrices(prod_name, uos_name,  price_unit)
                    this.model.set('price_udv', my_round(uos_pu, 2))
                    this.refresh()
                    break;
                case "price_udv":
                    var prod_name = this.$('.col-product').val();
                    var uos_name = this.$('.col-product_uos').val();
                    var uom_pu = this.getUomUosPrices(prod_name, uos_name, 0, value)
                    this.model.set('price_udv', my_round(value, 2));
                    this.model.set('pvp', my_round(uom_pu, 2));
                    this.refresh();
                    break;
                case "pvp":
                    var prod_name = this.$('.col-product').val();
                    var uos_name = this.$('.col-product_uos').val();
                    uos_pu = this.getUomUosPrices(prod_name, uos_name,  value)
                    this.model.set('price_udv', my_round(uos_pu, 2));
                    this.model.set('pvp', my_round(value, 2));
                    this.refresh();
                    break;

                // case "product_uos":
                //     this.model.set('product_uos', value);
                //     this.refresh();
                //     break;
                // case "unit":
                //     this.model.set('unit', value);
                //     this.refresh();
                //     break;
                // case "qnote":
                //     var qnote_id = this.ts_model.db.qnote_name_id[value]
                //     if (!qnote_id){
                //         alert(_t("Qnote name '" + value + "' does not exist"));
                //         this.model.set('qnote', "");
                //         this.refresh();
                //         break;
                //     }
                //     var qnote_obj = this.ts_model.db.get_qnote_by_id(qnote_id);
                //     this.model.set('qnote', qnote_obj.code);
                //     this.refresh();
                //     break;
                // case "detail":
                //     this.model.set('detail', value);
                //     this.refresh();
                //     break;
                case "discount":
                    this.model.set('discount', value);
                    this.refresh();
                    // Añadir nueva linea o cambiar el foco a la de abajo si la hubiera
                    var selected_line = self.order.selected_orderline;
                    if (selected_line){
                        var n_line = selected_line.get('n_line');
                        if (n_line == self.order_widget.orderlinewidgets.length){
                            $('.add-line-button').click()
                        }
                        else{
                            var next_line = self.order_widget.orderlinewidgets[n_line]
                            if(next_line){
                              self.order.selectLine(next_line.model);
                              next_line.$el.find('.col-code').focus();
                            }
                        }
                    }
                    break;
            }
        },
        refresh: function(){
            console.log("Refresh Line")
            var price = this.model.get("pvp")
            var qty = this.model.get("qty")
            var disc = this.model.get("discount")
            var subtotal = price * qty * (1 - (disc/ 100.0))
            this.model.set('total',subtotal);
            this.renderElement();

            // this.trigger('order_line_refreshed');
        },
    });

    module.OrderWidget = module.TsBaseWidget.extend({
        template:'Order-Widget',
        init: function(parent, options) {
            this._super(parent,options);
            this.ts_model.bind('change:selectedOrder', this.change_selected_order, this);
            this.bind_orderline_events();
            this.orderlinewidgets = [];
        },
        check_customer_get_id: function(){
            var client_name = this.ts_model.get('selectedOrder').get('partner')
            var client_id = this.ts_model.db.partner_name_id[client_name];
            if (!client_id){
                alert(_t('No customer defined'));
                return false
            }
            else{
                return client_id
            }
        },
        change_selected_order: function() {
            this.currentOrderLines.unbind();
            this.bind_orderline_events();
            this.renderElement();
        },
        bind_orderline_events: function() {
            this.currentOrderLines = (this.ts_model.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('add', this.renderElement, this);
            this.currentOrderLines.bind('remove', this.renderElement, this);
        },
        show_client: function(){"SIGIENTE LINEA"
            var client_id = this.check_customer_get_id()
            if (client_id){
                context = new instance.web.CompoundContext()
                var pop = new instance.web.form.FormOpenPopup(this);
                pop.show_element('res.partner',client_id,context,
                    {target:'new',
                     title: "Ver Cliente",
                     readonly: true,
               })

            }
        },
        show_product: function(product_id){
            if (product_id){
                context = new instance.web.CompoundContext()
                var pop = new instance.web.form.FormOpenPopup(this);
                pop.show_element('product.product',product_id,context,
                    {target:'new',
                     title: "Ver Producto",
                     readonly: true,
               })
            }
        },
        renderElement: function () {
            var self = this;
            this._super();

            this.$('.add-line-button').click(function(){
                var order =  self.ts_model.get('selectedOrder')
                var partner_id = self.ts_model.db.partner_name_id[order.get('partner')]
                if (!partner_id){
                    alert(_t('Please select a customer before adding a order line'));
                }else{
                    self.ts_model.get('selectedOrder').addLine();
                    var added_line = self.ts_model.get('selectedOrder').getLastOrderline();
                    self.ts_model.get('selectedOrder').selectLine(added_line);
                    self.orderlinewidgets[self.orderlinewidgets.length - 1].$el.find('.col-code').focus(); //set focus on line when we add one
                }
            });
            this.$('.remove-line-button').click(function(){
                self.ts_model.get('selectedOrder').removeLine();
                var selected_line = self.ts_model.get('selectedOrder').getSelectedLine();
                if (selected_line){
                    n_line = selected_line.get('n_line')
                    self.orderlinewidgets[n_line-1].$el.find('.col-code').focus();
                }

            });
            this.$('#ult-button').click(function(){
                var client_id = self.check_customer_get_id();
                if (client_id){
                    $.when(self.ts_model.get('selectedOrder').get_last_order_lines(client_id))
                        .done(function(){
                            // self.bind_orderline_events(); //in get_last_order_lines we unbid add event of currentOrderLines to render faster
                            // self.renderElement();
                            // self.ts_widget.new_order_screen.totals_order_widget.changeTotals();
                        })
                        .fail(function(){
                            alert(_t("NOT WORKING"));
                        })
                }
            });
            this.$('#vua-button').click(function(){
                var client_id = self.check_customer_get_id();
                if (client_id){
                    $.when(self.ts_model.get('selectedOrder').get_last_line_by('year', client_id))
                        .done(function(){
                            // self.bind_orderline_events(); //in get_last_line_by we unbid add event of currentOrderLines to render faster
                            // self.renderElement();
                            // self.ts_widget.new_order_screen.totals_order_widget.changeTotals();

                        })
                        .fail(function(){
                            alert(_t("NOT WORKING"));
                        })
                }
            });
            this.$('#so-button').click(function(){
                var client_id = self.check_customer_get_id();
                if (client_id){
                    $.when(self.ts_model.get('selectedOrder').get_last_line_by('3month', client_id))
                        .done(function(){
                            // self.bind_orderline_events(); //in get_last_line_by we unbid add event of currentOrderLines to render faster
                            // self.renderElement();
                            // self.ts_widget.new_order_screen.totals_order_widget.changeTotals();
                        })
                        .fail(function(){
                            alert(_t("NOT WORKING"));
                        })
                }
            });
            this.$('#promo-button').click(function(){
                alert(_t("Pending to develop"));
            });
             this.$('#sust-button').click(function(){
                var current_order = self.ts_model.get('selectedOrder')
                var selected_line = current_order.selected_orderline;
                if (!selected_line){
                    alert(_t("You must select a product line."));
                }else{
                    var product_id = self.ts_model.db.product_name_id[selected_line.get('product')];
                    if (!product_id){
                        alert(_t("This line has not a product defined."));
                    }
                    else{
                        var product_obj = self.ts_model.db.get_product_by_id(product_id);
                        if ($.isEmptyObject(product_obj.products_substitute_ids))
                            alert(_t("This product have not substitutes"));
                        else{
                            self.ts_model.set('sust_products', []);
                            for (key in product_obj.products_substitute_ids){
                                var sust_id = product_obj.products_substitute_ids[key];
                                var sust_obj = self.ts_model.db.get_product_by_tmp_id(sust_id);
                                self.ts_model.get('sust_products').push(sust_obj)
                            }
                            self.ts_widget.screen_selector.show_popup('product_sust_popup', false);
                        }
                    }
                }

            });
            this.$('#info-button').click(function(){
                var current_order = self.ts_model.get('selectedOrder')
                var selected_line = current_order.selected_orderline;
                if (!selected_line){
                    alert(("You must select a product line."));
                }else{
                    var product_id = self.ts_model.db.product_name_id[selected_line.get('product')];
                    if (!product_id){
                        alert(_t("This line has not a product defined."));
                    }
                    else{
                        self.show_product(product_id)
                    }
                }
            });
            this.$('#show-client').click(function(){

                self.show_client();
            });
            for(var i = 0, len = this.orderlinewidgets.length; i < len; i++){
                this.orderlinewidgets[i].destroy();
            }
            this.orderlinewidgets = [];

            var $content = this.$('.orderlines');
            // var $content = this.$('#effective-append'); #TODO NO CREO QUE SEA POSIBLE POR LO DE ELIMINAR
            var nline = 1
            this.currentOrderLines.each(_.bind( function(orderLine) {
                orderLine.set('n_line', nline++);
                var line = new module.OrderlineWidget(this, {
                    model: orderLine,
                    order: this.ts_model.get('selectedOrder'),
                });
                // line.on('order_line_selected', self, self.order_line_selected);
                // line.on('order_line_refreshed', self, self.order_line_refreshed);
                line.appendTo($content);
                self.orderlinewidgets.push(line);
            }, this));

        },
        order_line_selected: function(){
        },
        order_line_refreshed: function(){
        },
    });



    module.TotalsOrderWidget = module.TsBaseWidget.extend({
        template:'Totals-Order-Widget',
        init: function(parent, options) {
            this._super(parent,options);
            this.ts_model.bind('change:selectedOrder', this.change_selected_order, this);
            this.bind_orderline_events();
        },
        bind_orderline_events: function() {
            this.order_model = this.ts_model.get('selectedOrder');
            this.order_model.bind('change:selected_line', this.bind_selectedline_events, this);

            this.currentOrderLines = (this.ts_model.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('add', this.changeTotals, this);
            this.currentOrderLines.bind('remove', this.changeTotals, this);
        },
        bind_selectedline_events: function () {
            var self = this;

            this.selected_line = this.ts_model.get('selectedOrder').get('selected_line');
            this.selected_line.unbind('change:total');
            this.selected_line.unbind('change:weight');
            this.selected_line.unbind('change:boxes');
            this.selected_line.bind('change:total', this.changeTotals, this);
            this.selected_line.bind('change:weight', this.changeTotals, this);
            this.selected_line.bind('change:boxes', this.changeTotals, this);
        },
        change_selected_order: function() {
            this.order_model.unbind('change:selected_line');
            this.currentOrderLines.unbind();
            this.bind_orderline_events();
            this.renderElement();
        },
        renderElement: function () {
            var self = this;

            this.order_model = this.ts_model.get('selectedOrder');
            this._super();

            this.$('.confirm-button').click(function (){ self.confirmCurrentOrder() });
            this.$('.cancel-button').click(function (){ self.cancelCurrentOrder() });
            this.$('.save-button').click(function (){ self.saveCurrentOrder() });
        },
        changeTotals: function(){
            var self = this;
            this.base = 0;
            this.discount = 0;
            this.margin = 0;
            this.weight = 0;
            this.iva = 0;
            this.total = 0;
            this.pvp_ref = 0;
            this.sum_cmc = 0;
            this.sum_box = 0;
            this.sum_fresh = 0;
            (this.currentOrderLines).each(_.bind( function(line) {
                var product_id = self.ts_model.db.product_name_id[line.get('product')]
                if (product_id){
                    var product_obj = self.ts_model.db.get_product_by_id(product_id)
                    // if (product_obj.product_class == 'normal'){
                      self.sum_cmc += product_obj.cmc * line.get('qty');
                      self.sum_box += line.get('boxes');
                      self.weight += line.get('weight');
                      self.discount += line.get('pvp_ref') != 0 ? (line.get('pvp_ref') - line.get('pvp')) * line.get('qty') : 0;
                      self.margin += (line.get('pvp') -  product_obj.cmc) * line.get('qty');
                      self.pvp_ref += line.get('pvp_ref') * line.get('qty');
                      self.base += line.get_price_without_tax('total');
                      self.iva += line.get_tax();
                      self.total += line.get_price_with_tax();
                    // }
                    // else{
                    //     self.sum_fresh += line.get_price_without_tax('total');
                    // }
                }
            }, this));
            this.order_model.set('total_base', my_round(self.base, 2));
            this.order_model.set('total_iva', my_round(self.iva, 2));
            this.order_model.set('total', my_round(self.total, 2));
            this.order_model.set('total_weight', my_round(self.weight, 2));
            this.order_model.set('total_discount', my_round(self.discount, 2));
            var discount_per = (0).toFixed(2) + "%";
            if (self.pvp_ref != 0){
                var discount_num = (self.discount/self.pvp_ref) * 100 ;
                if (discount_num < 0)
                    var discount_per = "+" + my_round( discount_num * (-1) , 2).toFixed(2) + "%";
                else
                    var discount_per = my_round( discount_num , 2).toFixed(2) + "%";
            }
            this.order_model.set('total_discount_per', discount_per);
            this.order_model.set('total_margin', my_round(self.margin, 2));
            var margin_per = (0).toFixed(2) + "%";
            var margin_per_num = 0
            if (self.base != 0) {
                margin_per_num = my_round( ((self.base - self.sum_cmc) / self.base) * 100 , 2)
                margin_per = margin_per_num.toFixed(2) + "%"
            }
            this.order_model.set('total_margin_per', margin_per);
            this.order_model.set('total_boxes', self.sum_box); //integer
            this.order_model.set('total_fresh', self.sum_fresh);

            var min_limit = this.ts_model.get('company').min_limit
            var min_margin = this.ts_model.get('company').min_margin
            this.renderElement();
            if (margin_per_num < min_margin)
               this.$('#total_margin').addClass('warning-red');
            else
               $('#total_margin').removeClass('warning-red');
            if (self.total < min_limit)
                $('#total_order').addClass('warning-red');
            else
               $('#total_order').removeClass('warning-red');
        },
        confirmCurrentOrder: function() {
            var currentOrder = this.order_model;
            currentOrder.set('action_button', 'confirm')
            if ( (currentOrder.get('erp_state')) && (currentOrder.get('erp_state') != 'draft') ){
                alert(_t('You cant confirm an order which state is diferent than draft.'));
            }
            else if (currentOrder.get('limit_credit')*1 != 0 && currentOrder.get('customer_debt')*1 + currentOrder.get('total')*1 > currentOrder.get('limit_credit')*1){
                    alert(_t('You cant confirm this order because you are exceeding customer limit credit. Please save as draft'));
            }
           else if ( currentOrder.check() ){
                this.ts_model.push_order(currentOrder.exportAsJSON());
            }
        },
        cancelCurrentOrder: function() {
            var currentOrder = this.order_model;
            currentOrder.set('action_button', 'cancel')
            if ( (currentOrder.get('erp_state')) && (currentOrder.get('erp_state') != 'draft') ||  !currentOrder.get('erp_id')){
                alert(_t('You cant cancel an order which state is diferent than draft.'));
            }
            else if ( currentOrder.check() ){
                this.ts_model.cancel_order(currentOrder.get('erp_id'));
            }
        },
        saveCurrentOrder: function() {
            var currentOrder = this.order_model;
            currentOrder.set('action_button', 'save')
            if ( (currentOrder.get('erp_state')) && (currentOrder.get('erp_state') != 'draft') ){
                alert(_t('You cant save as draft an order which state is diferent than draft.'));
            }
            else if ( currentOrder.check() ){
                this.ts_model.push_order(currentOrder.exportAsJSON());
            }
        },

    });

     module.ProductInfoOrderWidget = module.TsBaseWidget.extend({
        template:'ProductInfo-Order-Widget',
        init: function(parent, options) {
            this._super(parent,options);
            this.ts_model.bind('change:selectedOrder', this.change_selected_order, this);
            this.order_model = this.ts_model.get('selectedOrder');
            this.selected_line = undefined;
            this.bind_selectedline_events();
            this.set_default_values();
        },
        set_default_values: function(){
            this.stock = "";
            this.date = "";
            this.qty = "";
            this.price = "";
            this.mark = "";
            this.unit_weight = "";
            this.min_price = "";
            this.margin = "";
            this.discount = "";
            this.n_line = "";
            this.class = "";
        },
        bind_selectedline_events: function(){
            this.order_model = this.ts_model.get('selectedOrder');
            this.order_model.bind('change:selected_line', this.calcProductInfo, this);
        },
        change_selected_order: function() {
            this.order_model.unbind('change:selected_line');
            this.bind_selectedline_events()
            this.set_default_values();
            this.renderElement();
        },
        renderElement: function () {
            var self = this;
            this.order_model = this.ts_model.get('selectedOrder');
            this._super();
        },
        calcProductInfo: function () {
            // debugger;
            var self = this;
            this.selected_line = this.ts_model.get('selectedOrder').get('selected_line');
            if (!this.selected_line.get("product")){
                this.set_default_values();
                this.renderElement();
            }
            this.selected_line.unbind('change:discount');
            this.selected_line.unbind('change:product');
            this.selected_line.unbind('change:margin');
            this.selected_line.bind('change:discount', this.change_discount, this);
            this.selected_line.bind('change:product', this.change_product, this);
            this.selected_line.bind('change:margin', this.change_margin, this);
            this.selected_line.trigger('change:product');
            if (this.selected_line){
                this.change_discount();
                this.change_margin();
            }

        },
        change_product: function(){
            // debugger;
            var self = this;
            var line_product = this.selected_line.get("product")
            self.n_line = self.selected_line.get('n_line') + " / " + self.ts_model.get('selectedOrder').get('orderLines').length;
            if (line_product != ""){
                var product_id = this.ts_model.db.product_name_id[line_product]
                var partner_name = this.ts_model.get('selectedOrder').get('partner');
                var partner_id = this.ts_model.db.partner_name_id[partner_name];
                if (product_id && partner_id){
                    var product_obj = this.ts_model.db.get_product_by_id(product_id)
                    var partner_obj = this.ts_model.db.get_partner_by_id(partner_id)
                    var pricelist_id = partner_obj.property_product_pricelist
                    var model = new instance.web.Model('product.product');
                    model.call("get_product_info",[product_id,partner_id,pricelist_id],{context:new instance.web.CompoundContext()})
                        .then(function(result){
                            self.stock = my_round(result.stock,2).toFixed(2);
                            self.date = result.last_date != "-" ? self.ts_model.localFormatDate(result.last_date.split(" ")[0]) : "-";
                            self.qty = my_round(result.last_qty,2).toFixed(2);
                            self.price = my_round(result.last_price,2).toFixed(2);
                            self.min_price = my_round(result.min_price,2).toFixed(2);
                            self.mark = result.product_mark;
                            self.class = result.product_class;
                            self.unit_weight = my_round(result.weight_unit,2).toFixed(2);
                            self.renderElement();
                        });
                }
                else{
                    this.set_default_values();
                    this.renderElement();
                }
            }
        },
        change_discount: function(){
            var discount = this.selected_line.get('discount');
            discount = discount * 100
            var discount_str = ""
            //check type?
            if (discount < 0){
                discount = discount * (-1); //remove negative sign
                discount_str = "+" + discount.toFixed(2) + "%";
            }else{
                discount_str = discount.toFixed(2) + "%";
            }
            this.discount = discount_str
            this.renderElement();
        },
        change_margin: function(){
            var margin = this.selected_line.get('margin');
            margin = margin * 100
            this.margin = margin.toFixed(2) + "%";
            this.renderElement();
        },
    });

    module.SustituteLineWidget = module.TsBaseWidget.extend({
        template:'Sustitute-Line-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.product = options.product;
        },
        add_product_to_order: function() {
            var product_id = this.product.id
            if (product_id){
                var current_order = this.ts_model.get('selectedOrder')
                current_order.removeLine();
                current_order.addProductLine(product_id);

                $('button#button_no').click();
            }
        },
        renderElement: function() {
            var self=this;
            this._super();
            this.$('.add-sustitute').click(_.bind(this.add_product_to_order, this));
        },
    });
    module.ProductSustWidget = module.TsBaseWidget.extend({
        template:'Product-Sust-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.line_widgets = [];
            this.sust_products =  [];
        },

        renderElement: function() {
            var self=this;
            this._super();

            for(var i = 0, len = this.line_widgets.length; i < len; i++){
                this.line_widgets[i].destroy();
            }
            this.line_widgets = [];
            var products = this.ts_model.get("sust_products");
            for (var i = 0, len = products.length; i < len; i++){
                var product_obj = products[i]
                var product_line = new module.SustituteLineWidget(self, {product: product_obj})
                this.line_widgets.push(product_line);
                product_line.appendTo(self.$('.sustitutelines'));
                this.$('.add-sustitute')[0].focus();
            }
        },
    });


    module.SoldProductLineWidget = module.TsBaseWidget.extend({
        template:'Sold-Product-Line-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.sold_line = options.sold_line;
        },

        renderElement: function() {
            var self=this;
            this._super();
            this.$('#add-line').off("click").click(_.bind(this.add_line_to_order, this));

        },
        add_line_to_order: function() {
            var self=this;
            self.ts_model.get('selectedOrder').add_lines_to_current_order([self.sold_line])
            //in get_last_order_lines we unbid add event of currentOrderLines to render faster
            self.ts_widget.new_order_screen.order_widget.bind_orderline_events();
            self.ts_widget.new_order_screen.order_widget.renderElement()
            self.ts_widget.new_order_screen.totals_order_widget.changeTotals();

        },
    });

    module.SoldProductWidget = module.TsBaseWidget.extend({
        template:'Sold-Product-Widget',
        init: function(parent, options){
            var self = this;
            this._super(parent,options);
            this.ts_model.get('sold_lines').bind('reset', function(){
                self.renderElement();
            });
            this.line_widgets = [];
        },

        renderElement: function() {
            var self=this;
            this._super();
            // free subwidgets  memory from previous renders
            for(var i = 0, len = this.line_widgets.length; i < len; i++){
                this.line_widgets[i].destroy();
            }
            this.line_widgets = [];
            var sold_lines = this.ts_model.get("sold_lines").models || []

            var $lines_content = this.$('.soldproductlines');
            for (var i=0, len = sold_lines.length; i < len; i++){
                var line_obj = sold_lines[i].attributes;
                var sold_line = new module.SoldProductLineWidget(self, {sold_line: line_obj})
                this.line_widgets.push(sold_line)
                sold_line.appendTo($lines_content)
            }
        },
    });
}
