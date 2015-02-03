function openerp_ts_new_order_widgets(instance, module){ //module is instance.point_of_sale
    var QWeb = instance.web.qweb,
    _t = instance.web._t;
    var round_pr = instance.web.round_precision
    var my_round = function(number, decimals){
        var n = number;
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
            this.order.bind('destroy',function(){ self.destroy(); });
            this.ts_model.bind('change:selectedOrder', _.bind( function(ts_model) {
                self.selectedOrder = ts_model.get('selectedOrder');
                self.selectedOrder.unbind('change:partner');
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
            $('.select-order').removeClass('selected-order');
            this.$el.addClass('select-order');
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

            //autocomplete products and units from array of names
            this.$('#partner_code').autocomplete({
                source: this.ts_model.get('customer_codes'),
            });
            this.$('#partner').autocomplete({
                source: this.ts_model.get('customer_names'),
            });
            
        },
        set_value: function(key) {
            var value = this.$('#'+key).val();
            this.order_model.set(key, value);
            this.perform_onchange(key, value);
        },
        perform_onchange: function(key, value) {
            if (!value) {return;}
            switch (key){
                case "partner_code":
                    partner_id = this.ts_model.db.partner_ref_id[value];
                    if (!partner_id){
                        alert(_t("Customer code '" + value + "' does not exist"));
                        this.order_model.set('partner', "");
                        this.order_model.set('partner_code', "");
                        this.refresh();
                        break;
                    }
                    partner_obj = this.ts_model.db.get_partner_by_id(partner_id);
                    this.order_model.set('partner', partner_obj.name);
                    this.order_model.set('limit_credit', my_round(partner_obj.credit_limit, 2));
                    this.order_model.set('customer_debt', my_round(partner_obj.credit, 2));
                    contact_obj = this.ts_model.db.get_partner_contact(partner_id); //If no contacts return itself
                    this.order_model.set('contact_name', contact_obj.name);
                    this.order_model.set('comercial', partner_obj.user_id ? partner_obj.user_id[1] : "");
                    this.refresh();
                    this.$('#date_invoice').focus();
                    break;

                case "partner":
                    partner_id = this.ts_model.db.partner_name_id[value];
                    if (!partner_id){
                        alert(_t("Customer name '" + value + "' does not exist"));
                        this.order_model.set('partner', "");
                        this.order_model.set('partner_code', "");
                        this.refresh();
                        break;
                    }
                    partner_obj = this.ts_model.db.get_partner_by_id(partner_id);
                    this.order_model.set('partner_code', partner_obj.ref ? partner_obj.ref : "");
                    this.order_model.set('limit_credit', my_round(partner_obj.credit_limit,2));
                    this.order_model.set('customer_debt', my_round(partner_obj.credit,2));
                    contact_obj = this.ts_model.db.get_partner_contact(partner_id); //If no contacts return itself
                    this.order_model.set('comercial', partner_obj.user_id ? partner_obj.user_id[1] : "");
                    this.order_model.set('contact_name', contact_obj.name);
                    this.refresh();
                    this.$('#partner_code').focus();
                    break;

                case "date_invoice":
                    this.$('#date_planed').focus();
                    break;
                case "date_planed":
                    this.$('#date_order').focus();
                    break;
                case "date_invoice":
                    this.$('#partner').focus();
                    break;
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
            this.model = options.model;
            this.order = options.order;
            this.price_and_min = false;

            this.model.bind('change_line', this.refresh, this); //#TODO entra demasiadas veces por la parte esta
        },
        click_handler: function() {
            this.order.selectLine(this.model);
            this.trigger('order_line_selected');
            // this.$('.col-code').focus();
        },
        renderElement: function() {
            var self=this;
            this._super();
            this.$el.click(_.bind(this.click_handler, this));
            if(this.model.is_selected()){
                this.$el.addClass('selected');
            }
            this.$('.col-code').blur(_.bind(this.set_value, this, 'code'));
            this.$('.col-product').blur(_.bind(this.set_value, this, 'product')); //porque con change no va??
            this.$('.col-unit').blur(_.bind(this.set_value, this, 'unit')); // con change no va???
            this.$('.col-qty').change(_.bind(this.set_value, this, 'qty'));
            this.$('.col-pvp').change(_.bind(this.set_value, this, 'pvp'));
            this.$('.col-total').change(_.bind(this.set_value, this, 'total'));

           //autocomplete products and units from array of names
            var products_ref = this.ts_model.get('visible_products')[this.ts_model.db.partner_name_id[this.order.get('partner')]][1]
            // console.log ("PARTNER PRODUCT CODES: " + this.order.get('partner') + " = " + products_ref)
            this.$('.col-code').autocomplete({
                source: products_ref,
            });
            var product_names = this.ts_model.get('visible_products')[this.ts_model.db.partner_name_id[this.order.get('partner')]][0]
            // console.log ("PRODUCTS PARTNER: " + this.order.get('partner') + " = " + product_names)
            this.$('.col-product').autocomplete({
                // source: this.ts_model.get('products_names'),
                source: product_names,
            });
            this.$('.col-unit').autocomplete({
                source:this.ts_model.get('units_names')
            });
        },
        set_value: function(key) {
            var value = this.$('.col-'+key).val();
            var set=true;
            if (key == 'qty' || key == 'pvp' || key == 'total' ){
                if (isNaN(value)){
                    this.$('.col-'+key).val(this.model.get(key));
                    alert(_t(value + " is not a valid number"));
                    set=false;
                }
                else
                    value = my_round(value,2);
            }
            if (set){
                if ( this.model.get(key) != value ){
                    this.model.set(key, value);
                    this.perform_onchange(key);
                }
            }
        },
        get_default_unit_name: function(product_obj){
            var res = "";
            var unit;
            switch (product_obj.min_unit){
                case "unit":
                    unit = this.ts_model.db.get_like_type_unit("units")
                    res = unit.name
                    break;
                case "box":
                    unit = this.ts_model.db.get_like_type_unit("boxes")
                    res = unit.name
                    break;
                case "both":
                    unit = this.ts_model.db.get_like_type_unit("units")
                    res = unit.name
                    break;
                default:
                    unit = this.ts_model.db.get_like_type_unit("units")
                    res = unit.name
            }
            return res
        },
        update_stock_product: function(product_id){
            var self=this;
            var domain = [['id', '=', product_id]]
            var loaded = self.ts_model.fetch('product.product',
                                            ['name','product_class','list_price','cmc','default_code','uom_id','virtual_stock_conservative','taxes_id', 'weight', 'kg_un', 'un_ca', 'ca_ma', 'ma_pa', 'products_substitute_ids', 'min_unit'],
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
                            model.call("product_id_change",[[],pricelist_id,product_id],kwargs)
                            .then(function(result){
                                var product_obj = self.ts_model.db.get_product_by_id(product_id);
                                var uom_obj = self.ts_model.db.get_unit_by_id(product_obj.uom_id[0])
                                self.model.set('fresh_price', my_round(result.value.last_price_fresh || 0,2));
                                self.model.set('code', product_obj.default_code || "");  
                                self.model.set('product', product_obj.name || "");  
                                self.model.set('taxes_ids', result.value.tax_id || []); //TODO poner impuestos de producto o vacio
                                self.model.set('unit', self.get_default_unit_name(product_obj) || "" );
                                self.model.set('qty', 1);
                                self.model.set('discount', 0);
                                self.model.set('weight', my_round(product_obj.weight || 0,2));
                                self.model.set('boxes', uom_obj ? self.ts_model.convert_units_to_boxes(uom_obj, product_obj, 1) : 0);
                                if (!result.value.price_unit || result.value.price_unit == 'warn') {
                                    result.value.price_unit = 0;
                                }
                                self.model.set('pvp_ref', my_round( (result.value.price_unit != 0 && product_obj.product_class != "fresh") ? result.value.price_unit : 0,2 ));
                                self.model.set('pvp', my_round(result.value.price_unit || 0,2));
                                self.model.set('total', my_round(result.value.price_unit || 0,2));
                                self.model.set('margin', my_round( (result.value.price_unit != 0 && product_obj.product_class != "fresh") ? ( (result.value.price_unit - product_obj.cmc) / result.value.price_unit) : 0 , 2));
                                if ( (1 > product_obj.virtual_stock_conservative) && (product_obj.product_class != "fresh") && (product_obj.product_class != "ultrafresh") ){
                                    alert(_t("You want sale 1 " + " " + product_obj.uom_id[1] + " but only " +  product_obj.virtual_stock_conservative + " available."))
                                    var new_qty = (product_obj.virtual_stock_conservative < 0) ? 0.0 : product_obj.virtual_stock_conservative
                                    self.model.set('qty', new_qty);
                                    self.refresh();
                                } 
                                self.refresh();
                                self.$('.col-unit').focus()
                            });
                        })
                        .fail(function(){
                            alert(_t("NOT WORKING"));
                        })
        },
        call_onchange_price_unit: function(product_id){
            var self=this;
            var res=false;
            var customer_id = this.ts_model.db.partner_name_id[this.order.get('partner')];
            // var kwargs = {context: new instance.web.CompoundContext({}),
            //             }
            var pricelist_id = (this.ts_model.db.get_partner_by_id(customer_id)).property_product_pricelist;
            var model = new instance.web.Model("product.pricelist");
            model.call("ts_get_product_pvp",[product_id,pricelist_id])
                .then(function(result){
                    return result
                });
        },
        perform_onchange: function(key) {
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
                    // this.refresh()

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
                    // this.refresh();
                    break; 
                    
                case "qty":
                    
                    // CALC BOXES
                    var prod_name = this.$('.col-product').val();
                    var product_id = this.ts_model.db.product_name_id[prod_name];
                    if (!product_id){
                        alert(_t("Product name '" + prod_name + "' does not exist"));
                        this.model.set('qty', "1");
                        this.refresh();
                        break;
                    }
                    var uom_name = this.$('.col-unit').val();
                    var uom_id = this.ts_model.db.unit_name_id[uom_name];
                    if (!uom_id){
                        alert(_t("Unit of measure '" + uom_name + "' does not exist"));
                        this.model.set('qty', 1);
                        this.refresh();
                        break;
                    }
                    var product_obj = this.ts_model.db.get_product_by_id(product_id);
                    if ( (value > product_obj.virtual_stock_conservative) && (product_obj.product_class != "fresh") && (product_obj.product_class != "ultrafresh") ){
                        alert(_t("You want sale " + value + " " + uom_name + " but only " +  product_obj.virtual_stock_conservative + " available."))
                        var new_qty = (product_obj.virtual_stock_conservative < 0) ? 0.0 : product_obj.virtual_stock_conservative
                        this.model.set('qty', new_qty);
                        this.refresh();
                        break;
                    } 
                    var uom_obj = this.ts_model.db.get_unit_by_id(uom_id);
                    var boxes = this.ts_model.convert_units_to_boxes(uom_obj, product_obj, value);
                    this.model.set('boxes', boxes);

                    //change pvp
                    var line_pvp = this.model.get('pvp');
                    this.model.set('total', my_round(value * line_pvp,2));

                    //change weight
                    var weight =  this.model.get('weight')
                    this.model.set('weight', my_round(value * weight,2));
                    this.refresh();
                    break;
                case "pvp":
                    var self=this;
                    var prod_name = this.$('.col-product').val();
                    var product_id = this.ts_model.db.product_name_id[prod_name];
                    if (!product_id){
                        alert(_t("Product name '" + prod_name + "' does not exist"));
                        // this.model.set('code', "");
                        // this.model.set('product', "");
                        // this.refresh();
                        break;
                    }
                    var customer_id = this.ts_model.db.partner_name_id[this.order.get('partner')];
                    var pricelist_id = (this.ts_model.db.get_partner_by_id(customer_id)).property_product_pricelist;
                    var model = new instance.web.Model("product.pricelist");
                    model.call("ts_get_product_pvp",[product_id,pricelist_id])
                        .then(function(result){
                            if (result[1] && (value < result[1]) ){
                                alert(_t("Current pvp is lower than minimum price"));
                                // self.model.set('pvp',result[1]);
                                self.refresh();
                            }
                                //Calc discount line
                                var product_obj = self.ts_model.db.get_product_by_id(product_id);
                                var orig_product_price = self.model.get('pvp_ref')
                                if (orig_product_price != 0) {
                                    discount = 1 - (value / orig_product_price);
                                }else {
                                    discount = 0;
                                }
                                var line_margin = (value && product_obj.product_class != "fresh") ? ((value - product_obj.cmc) / value) : 0
                                self.model.set('margin', line_margin);
                                // self.model.set('discount', my_round(discount,2));
                                self.model.set('discount', discount);
                                var val2 = self.model.get('qty')*1;
                                self.model.set('total', my_round(value * val2,2));
                                self.refresh();
                        });
                    break;
                case "unit":
                    var uom_id = this.ts_model.db.unit_name_id[value]
                    if (!uom_id){
                        alert(_t("Unit name '" + value + "' does not exist"));
                        this.model.set('unit', "");
                        this.refresh();
                        break;
                    }
                    var prod_name = this.$('.col-product').val();
                    var product_id = this.ts_model.db.product_name_id[prod_name];
                    if (!product_id){
                        alert(_t("Product name '" + prod_name + "' does not exist"));
                        this.model.set('unit', "");
                        this.refresh();
                        break;
                    }
                    var uom_obj = this.ts_model.db.get_unit_by_id(uom_id);
                    var product_obj = this.ts_model.db.get_product_by_id(product_id);
                    if (uom_obj.like_type == 'units'){
                        if (product_obj.min_unit == 'box'){
                            var unit = this.ts_model.db.get_like_type_unit('boxes');
                            alert(_t("This product only can be sale in boxes"));
                            this.model.set('unit', unit.name);
                            this.refresh();
                        }
                    }
                    if (uom_obj.like_type == 'boxes'){
                        if (product_obj.min_unit == 'unit'){
                            alert(_t("This product only can be sale in units"));
                            var unit = this.ts_model.db.get_like_type_unit('units');
                            this.model.set('unit', unit.name);
                            this.refresh();
                        }
                    }
                    var qty = this.$('.col-qty').val() || 1;
                    var boxes = this.ts_model.convert_units_to_boxes(uom_obj, product_obj, qty);
                    this.model.set('boxes', boxes);
            }
        },
        refresh: function(){
            this.renderElement();
            this.trigger('order_line_refreshed');
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
        show_client: function(){
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
            });
            this.$('#ult-button').click(function(){
                var client_id = self.check_customer_get_id();
                if (client_id){
                    $.when(self.ts_model.get('selectedOrder').get_last_order_lines(client_id))
                        .done(function(){
                            self.bind_orderline_events(); //in get_last_order_lines we unbid add event of currentOrderLines to render faster
                            self.renderElement();
                            self.ts_widget.new_order_screen.totals_order_widget.changeTotals();
                        })
                        .fail(function(){
                            alert(_t("NOT WORKING"));
                        })
                }
            });
            this.$('#vum-button').click(function(){
                var client_id = self.check_customer_get_id();
                if (client_id){
                    $.when(self.ts_model.get('selectedOrder').get_last_line_by('month', client_id))
                        .done(function(){
                            self.bind_orderline_events(); //in get_last_line_by we unbid add event of currentOrderLines to render faster
                            self.renderElement(); 
                            self.ts_widget.new_order_screen.totals_order_widget.changeTotals();

                        })
                        .fail(function(){
                            alert(_t("NOT WORKING"));
                        })
                }
            });
            this.$('#via-button').click(function(){
                var client_id = self.check_customer_get_id();
                if (client_id){
                    $.when(self.ts_model.get('selectedOrder').get_last_line_by('year', client_id))
                        .done(function(){
                            self.bind_orderline_events(); //in get_last_line_by we unbid add event of currentOrderLines to render faster
                            self.renderElement(); 
                            self.ts_widget.new_order_screen.totals_order_widget.changeTotals();
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
                                var sust_obj = self.ts_model.db.get_product_by_id(sust_id);
                                self.ts_model.get('sust_products').push(sust_obj)
                                self.ts_widget.screen_selector.show_popup('product_sust_popup');
                            }
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
                line.on('order_line_selected', self, self.order_line_selected);
                line.on('order_line_refreshed', self, self.order_line_refreshed);
                line.appendTo($content);
                self.orderlinewidgets.push(line);
            }, this));

        },
        order_line_selected: function(){
            // console.log("Click linea.")
        },
        order_line_refreshed: function(){
            // console.log("refreshed.")
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
                    if (product_obj.product_class !== 'fresh'){
                        self.sum_cmc += product_obj.cmc * line.get('qty');
                        self.sum_box += line.get('boxes');
                        self.weight += line.get('weight');
                        self.discount += line.get('pvp_ref') != 0 ? (line.get('pvp_ref') - line.get('pvp')) * line.get('qty') : 0;
                        self.margin += (line.get('pvp') -  product_obj.cmc) * line.get('qty');
                        self.pvp_ref += line.get('pvp_ref') * line.get('qty');
                        self.base += line.get_price_without_tax('total');
                        self.iva += line.get_tax();
                        self.total += line.get_price_with_tax();
                       
                    }
                    else{
                        self.sum_fresh += line.get('fresh_price');
                    }
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
                    // console.log(product_obj);
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
            // console.log("DISCOUNT = " + discount)
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
            // console.log("MARGIN = " + margin)
            margin = margin * 100
            var margin_str = ""
            // //check type?
            // if (margin < 0){
            //     margin = margin * (-1); //remove negative sign
            //     margin_str = "+" + margin.toFixed(2) + "%";
            // }else{
                margin_str = margin.toFixed(2) + "%";
            // }
            this.margin = margin_str
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
            // this.ts_model.get('orders').add(new module.Order({ ts_model: self.ts_model, contact_name: 'aaa' }));
            // var self=this;
            var product_id = this.product.id
            if (product_id){
                var current_order= this.ts_model.get('selectedOrder')
                current_order.addProductLine(product_id);
                // this.ts_widget.screen_selector.set_current_screen('new_order');
                // current_order.selectLine(current_order.get('orderLines').last());
                $('button#button1').click();
            }
        },
        renderElement: function() {
            var self=this;
            this._super();
            // this.$el.click(function(){self.show_product_info();});
            // this.$('.show-product').click(_.bind(this.show_product_info, this));
            this.$('.add-sustitute').click(_.bind(this.add_product_to_order, this));
        },
    });
    module.ProductSustWidget = module.TsBaseWidget.extend({
        template:'Product-Sust-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.line_widgets = [];
            this.sust_products =  [];
            // this.ts_model.get('sust_products').bind('change', this.renderElement, this);
        },

        renderElement: function() {
            var self=this;
            this._super();

            for(var i = 0, len = this.line_widgets.length; i < len; i++){
                this.line_widgets[i].destroy();
            }
            this.line_widgets = []; 
            var products = this.ts_model.get("sust_products");
            // var products = this.ts_model.get("products").models || [];
            for (var i = 0, len = products.length; i < len; i++){
                var product_obj = products[i]
                // var product_obj = products[i].attributes;
                var product_line = new module.SustituteLineWidget(self, {product: product_obj})
                this.line_widgets.push(product_line);
                product_line.appendTo(self.$('.sustitutelines'));
                this.$('.add-sustitute')[0].focus();
            }
        },
    });
}