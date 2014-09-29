function openerp_ts_models(instance, module){
    var QWeb = instance.web.qweb;
    _t = instance.web._t;
    var round_pr = instance.web.round_precision
    var round_dc = instance.web.round_decimals
    var my_round = function(number, decimals){
        var n = number;
        if (typeof n === "string"){
            n = n * 1;
        }
        return n.toFixed(decimals) * 1
    };
// ***************************** ********** BASE TELESALE MODEL ***********************************************

    // var round_di = instance.web.round_decimals;
    // var round_pr = instance.web.round_precision;

    // The TsModel contains the Telesale suystem representation of the backend.
    // Since the TS must work in standalone ( Without connection to the server ) 
    // it must contains a representation of the server's TS backend. 
    // (taxes, product list, configuration options, etc.)  this representation
    // is fetched and stored by the TsModel at the initialisation. 
    // this is done asynchronously, a ready deferred alows the GUI to wait interactively 
    // for the loading to be completed 
    // There is a single instance of the PosModel for each Front-End instance, it is usually called
    // 'pos' and is available to all widgets extending PosWidget.

    module.TsModel = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            var  self = this;
            this.session = session;  // openerp session
            this.ready = $.Deferred(); // used to notify the GUI that the PosModel has loaded all resources
            // this.flush_mutex = new $.Mutex();  // used to make sure the orders are sent to the server once at time
            this.db = new module.TS_LS();                       // a database used to store the products and categories
            this.db.clear('products','partners');
            // this.debug = jQuery.deparam(jQuery.param.querystring()).debug !== undefined;

            this.set({
                'currency': {symbol: $, position: 'after'},
                'shop':                 null,
                'user':                 null,
                'company':              null,
                'orders':               new module.OrderCollection(),
                'products':             new module.ProductCollection(),
                'calls':             new module.CallsCollection(),
                'product_search_string': "",
                'products_names':            [], // Array of products names
                'products_codes':            [], // Array of products code
                'sust_products':            [], // Array of products sustitutes
                'taxes':                null,
                'ts_session':           null,
                'ts_config':            null,
                'units':                [], // Array of units
                'units_names':          [], // Array of units names
                'customer_names':          [], // Array of customer names
                'customer_codes':          [], // Array of customer refs
                'pricelist':            null,
                'selectedOrder':        null,
                'nbr_pending_operations': 0,
                'visible_products': {},
                'call_id': false,


            });

            this.get('orders').bind('remove', function(){ self.on_removed_order(); });

            // We fetch the backend data on the server asynchronously. this is done only when the TS user interface is launched,
            // Any change on this data made on the server is thus not reflected on the telesale system until it is relaunched. 
            // when all the data has loaded, we compute some stuff, and declare the Ts ready to be used. 
            $.when(this.load_server_data())
                .done(function(){
                    self.get_products_by_partner();
                    self.log_loaded_data(); //Uncomment if you want to log the data to the console for easier debugging
                    self.check_dates();
                    
                }).fail(function(){
                    //we failed to load some backend data, or the backend was badly configured.
                    //the error messages will be displayed in PosWidget
                    self.ready.reject();
                });
        },
        check_dates: function(){
            var self = this;
            if ($.isEmptyObject(this.db.unit_by_id)){
                alert(_t("There is no units of measure. Please check the equals to field is seted in the desired units"));
                self.ready.reject();
            }
            else{
                self.ready.resolve();
            }
        },
        get_products_by_partner: function(){
            var self = this;
            for (key in this.db.partner_name_id){
                var partner_id = this.db.partner_name_id[key];
                var model = new instance.web.Model('res.partner');
                model.call("get_visibele_products_names",[partner_id],{context:new instance.web.CompoundContext()})
                    .then(function (result){
                        // debugger;
                        for (key in result){
                            self.get('visible_products')[key] = result[key]

                        }

                        
                    });
                
            }
        },
        // helper function to load data from the server
        fetch: function(model, fields, domain, ctx){
            console.log("BBBBBBBBBB")
            return new instance.web.Model(model).query(fields).filter(domain).context(ctx).all()
        },
         // helper function to load last_
        fetch_limited_ordered: function(model, fields, domain, limit, orderby, ctx){
            return new instance.web.Model(model).query(fields).filter(domain).limit(limit).order_by(orderby).context(ctx).first()
        },

        // loads all the needed data on the sever. returns a deferred indicating when all the data has loaded. 
        load_server_data: function(){
            var self=this;

            var loaded = self.fetch('res.users',['name','company_id'],[['id', '=', this.session.uid]])
                .then(function(users){
                    self.set('user',users[0]);

                    return self.fetch('res.company',
                    [
                        'currency_id',
                        'email',
                        'website',
                        'company_registry',
                        'vat',
                        'name',
                        'phone',
                        'partner_id',
                        'min_limit',
                        'min_margin',
                    ],
                    [['id','=',users[0].company_id[0]]]);
                }).then(function(companies){
                    self.set('company',companies[0]);

                    return self.fetch('product.uom', ['name', 'like_type'], [['like_type', '!=', '']]);
                    // return self.fetch('product.uom', ['name', 'like_type'], null);
                }).then(function(units){
                    // self.set('units',units);
                    for (key in units){
                        self.get('units_names').push(units[key].name)
                    }
                    
                    self.db.add_units(units);
                    
                     return self.fetch(
                        'product.product', 
                        ['name', ,'product_class','list_price','cmc','default_code','uom_id','virtual_stock_conservative','taxes_id', 'weight', 'kg_un', 'un_ca', 'ca_ma', 'ma_pa', 'products_substitute_ids'],
                        [['sale_ok','=',true]]
                        // {pricelist: self.get('shop').pricelist_id[0]} // context for price
                    );
                }).then(function(products){
                    for (key in products){
                        self.get('products_names').push(products[key].name);
                        self.get('products_codes').push(products[key].default_code);
                    }
                    self.db.add_products(products);

                    return self.fetch('res.partner',['name','ref', 'property_account_position', 'property_product_pricelist', 'credit', 'credit_limit', 'child_ids', 'phone', 'type', 'user_id'], [['customer','=',true]])
                }).then(function(customers){
                    for (key in customers){
                        self.get('customer_names').push(customers[key].name);
                        self.get('customer_codes').push(customers[key].ref);
                    }
                    self.db.add_partners(customers);

                    return self.fetch('account.tax', ['amount', 'price_include', 'type'], [['type_tax_use','=','sale']]);
                }).then(function(taxes) {
                    self.set('taxes', taxes);
                    self.db.add_taxes(taxes);
                    return self.fetch('account.fiscal.position.tax', ['position_id', 'tax_src_id', 'tax_dest_id']);

                    
                }).then(function(fposition_map) {
                    
                    self.db.add_taxes_map(fposition_map);
                    return self.fetch('account.fiscal.position', ['name', 'tax_ids']);
                }).then(function(fposition) {
                    self.db.add_fiscal_position(fposition);
                    // debugger;
                })

            return loaded;
        },
        // logs the usefull posmodel data to the console for debug purposes
        log_loaded_data: function(){
            // console.log('TsModel data has been loaded:');
            // // console.log('TsModel: units:',this.get('units'));
            // console.log('TsModel: taxes:',this.get('taxes'));
            // console.log('TsModel: Dbproducts:',this.db.product_by_id);
            // // console.log('TsModel: shop:',this.get('shop'));
            // console.log('TsModel: company:',this.get('company'));
            // // console.log('TsModel: currency:',this.get('currency'));
            // // console.log('TsModel: user_list:',this.get('user_list'));
            // console.log('TsModel: user:',this.get('user'));
            // // console.log('TsModel.session:',this.session);
            // console.log('TsModel end of data log.');
        },

        add_new_order: function(){
            var order = new module.Order({ts_model:this});
            this.get('orders').add(order);
            this.set('selectedOrder', order);
        },
        on_removed_order: function(removed_order){
            if( this.get('orders').isEmpty()){
                this.add_new_order();
            }else{
                this.set({ selectedOrder: this.get('orders').last() });
            }
        },
        push_order: function(record) {
            this.db.add_order(record);
            this.flush();
        },
        cancel_order: function(erp_id){
            var self = this;
            // (new instance.web.Model('sale.order')).call('cancel_order_from_ui',,undefined,{shadow:true})
            (new instance.web.Model('sale.order')).call('cancel_order_from_ui', [[erp_id]], {context:new instance.web.CompoundContext()})
                .fail(function(unused, event){
                    //don't show error popup if it fails 
                    // event.preventDefault();
                    console.error('Failed to cancel order:',erp_id);
                })
                .done(function(){
                    //remove from db if success
                    self.get('selectedOrder').destroy(); // remove order from UI
                });
        },
        flush: function() {
            this._flush(0);
        },
        // attempts to send an order of index 'index' in the list of order to send. The index
        // is used to skip orders that failed.
        _flush: function(index) {
            var self = this;
            var orders = this.db.get_orders();
            self.set('nbr_pending_operations',orders.length);
            var order  = orders[index];
            if(!order){
                return;
            }
            //try to push an order to the server
            // shadow : true is to prevent a spinner to appear in case of timeout
            // (new instance.web.Model('sale.order')).call('create_order_from_ui',[[order]],undefined,{shadow:true})
            (new instance.web.Model('sale.order')).call('create_order_from_ui',[[order]],{context:new instance.web.CompoundContext()})
                .fail(function(unused, event){
                    //don't show error popup if it fails 
                    // event.preventDefault();
                    console.error('Failed to send order:',order);
                    self._flush(index+1);
                })
                .done(function(){
                    //remove from db if success
                    self.db.remove_order(order.id);
                    self._flush(index);
                    self.get('selectedOrder').destroy(); // remove order from UI
                });
        },
        convert_units_to_boxes: function(uom_obj, product_obj, qty){
            var unit = uom_obj.like_type;
            var result = 0;
            switch (unit) {
                case "kg":
                    if (product_obj.kg_un != 0 && product_obj.kg_un != 0){
                        result = Math.ceil((qty / product_obj.kg_un) / (product_obj.un_ca));
                    }
                    
                    //# TO DO round result up.
                    break;
                case "units":
                    if (product_obj.un_ca != 0){
                        result = Math.ceil(qty / product_obj.un_ca);
                    }
                    //# TO DO round result up.
                    break;
                case "boxes":
                    result = Math.ceil(qty);
                    break;
                case "mantles":
                    result =Math.ceil( qty * product_obj.ca_ma);
                    break;
                case "palets":
                    result = Math.ceil( qty * product_obj.ma_pa * product_obj.ca_ma);
                    break;
            }
            // console.log("RESULT BOXES = ",result);
            return result;
        },
        // build a order loaded from the server as order_obj the selected order_model
        build_order: function(order_obj, order_model, order_lines){
            // var self=this;
            // console.log(order_obj, order_model, order_lines);
            var partner_obj = this.db.get_partner_by_id(order_obj.partner_id[0]);
            order_model.set('partner', partner_obj.name);
            order_model.set('partner_code', partner_obj.ref || "");
            order_model.set('customer_debt', partner_obj.credit);
            order_model.set('limit_credit', partner_obj.credit_limit);
            order_model.set('erp_id', order_obj.id);
            order_model.set('erp_state', order_obj.state);
            var state = order_obj.state
            if (order_obj.state == "draft")
                state = "borrador";
            else if(order_obj.state == "progress") 
                state = "En progreso";
            else if(order_obj.state == "cancel") 
                state = "Cancelado";
            else if(order_obj.state == "done")
                state = "Realizado";
            order_model.set('state', state);
            order_model.set('date_invoice', order_obj.date_invoice);
            order_model.set('num_order',order_obj.name);
            for (key in order_lines){
                var line = order_lines[key];
                var prod_obj = this.db.get_product_by_id(line.product_id[0]);
                var line_vals = {ts_model: this, order:order_model,
                                 code:prod_obj.default_code || "" ,
                                 product:prod_obj.name,
                                 unit:line.product_uom[1],
                                 qty:line.product_uom_qty,
                                 pvp:my_round(line.price_unit,2), //TODO poner precio del producto???
                                 total: my_round(line.price_subtotal,2),
                                 discount: my_round( ((line.pvp_ref == 0) ? 0: 1 - (line.price_unit / line.pvp_ref)), 2 ),
                                 weight: my_round(prod_obj.weight * line.product_uom_qty,2),
                                 margin: my_round( ( (line.price_unit != 0 && prod_obj.product_class != "fresh") ? ( (line.price_unit - prod_obj.cmc) / line.price_unit) : 0 ), 2),
                                 taxes_ids: line.tax_id || prod_obj.taxes_id || [],
                                 pvp_ref: line.pvp_ref,
                                 boxes: this.convert_units_to_boxes(this.db.get_unit_by_id(line.product_uom[0]),prod_obj,line.product_uom_qty)
                                }
                // console.log("line vaaaaaaaals");
                // console.log(line_vals);
                var line = new module.Orderline(line_vals);
                order_model.get('orderLines').add(line);
            }
        },
        parse_duration_watch_format: function(minutes){
            var res = "00:00";
            if (minutes){
                var int_part = Math.floor(minutes); // integer part of minutes
                var decimal_part = minutes - int_part;
                var seconds = Math.round(decimal_part * 60);
                if (int_part < 10) int_part = "0" + int_part;
                if (seconds < 10) seconds = "0" + seconds;
                res = int_part + ":" + seconds
            }
            return res;
        },
        get_calls_by_date_state: function(date, state){
            var self=this;
            if (date){
                var domain = [['user_id', '=', self.get('user').id],['date', '>=', date + " 00:00:00"],['date', '<=', date + " 23:59:59"],['partner_id', '!=', false]]
                if (state){
                    if (state != "any")
                        domain.push(['state','=',state])
                }
                // console.log('domain', domain);
                var context = new instance.web.CompoundContext()
                self.fetch('crm.phonecall',['date','partner_id','name','partner_phone','state','duration'],domain,context)
                .then(function(calls){
                    if (!$.isEmptyObject(calls)){
                        
                        for (key in calls){
                            calls[key].date = self.parse_utc_to_str_date(calls[key].date); //set dates in browser timezone
                            calls[key].duration = self.parse_duration_watch_format(calls[key].duration); //set dates in browser timezone
                            calls[key].partner_phone = self.db.get_partner_contact(calls[key].partner_id[0]).phone|| "-" //set phone of contact
                            calls[key].contact_name = self.db.get_partner_contact(calls[key].partner_id[0]).name //add contact name to phone
                        }
                        // console.log("EEEEEEEEEEEE CAAAAAAAAAAAAAAAAAALLLS ", calls)
                    }
                    self.get('calls').reset(calls);
                });
            }
        },
        getCurrentFullDateStr: function() {
            var date = new Date();
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            var hours = date.getHours();
            var minutes = date.getMinutes();
            var seconds = date.getSeconds();
            if (month < 10) month = "0" + month;
            if (day < 10) day = "0" + day;
            if (hours < 10) hours = "0" + hours;
            if (minutes < 10) minutes = "0" + minutes;
            if (seconds < 10) seconds = "0" + seconds;

            var today = year + "-" + month + "-" + day + " " + hours + ":" + minutes + ":" + seconds;
            return today;  
        },
        datetimeToStr: function(date) {
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            var hours = date.getHours();
            var minutes = date.getMinutes();
            var seconds = date.getSeconds();
            if (month < 10) month = "0" + month;
            if (day < 10) day = "0" + day;
            if (hours < 10) hours = "0" + hours;
            if (minutes < 10) minutes = "0" + minutes;
            if (seconds < 10) seconds = "0" + seconds;

            var today = year + "-" + month + "-" + day + " " + hours + ":" + minutes + ":" + seconds;
            return today;  
        },
        getCurrentDateStr: function() {
            var date = new Date();
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            if (month < 10) month = "0" + month;
            if (day < 10) day = "0" + day;

            var today = year + "-" + month + "-" + day;
            return today;  
        },
        parse_str_date_to_utc: function(str_date){
            return instance.web.datetime_to_str(Date.parse(str_date));
        },
        parse_utc_to_str_date: function(str_date){
            return this.datetimeToStr(instance.web.str_to_datetime(str_date));
        },
        dateToStr: function(date) {
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            if (month < 10) month = "0" + month;
            if (day < 10) day = "0" + day;

            var today = year + "-" + month + "-" + day;
            return today;
        },
        localFormatDate: function(date){
            var splited =  date.split("-");
            return splited[2] + "-" +  splited[1] + "-" + splited[0];
        },
        localFormatDateTime: function(date_time){
            var splited =  date_time.split(" ");
            var date_part =  splited[0].split('-');
            var hour_part =  splited[1];
            return date_part[2] + "-" +  date_part[1] + "-" + date_part[0] + " " + hour_part;
        }


    });
//**************************** PRODUCTS AND PRODUCT COLLECTION****************************************************
    module.Product = Backbone.Model.extend({
    });
    
    module.ProductCollection = Backbone.Collection.extend({
        model: module.Product,
    });


// **************************** ORDER LINE AND ORDER LINE COLLECTION***********************************************
    module.Orderline = Backbone.Model.extend({
        defaults: {
            n_line: '',
            code: '',
            product: '',
            unit: '',
            qty: 1,
            pvp: 0,
            pvp_ref: 0, //in order to change the discount
            total: 0,
            //to calc totals
            discount: 0,
            weight: 0,
            boxes: 0,
            margin: 0,
            taxes_ids: [],
            temperature: 0,   
            fresh_price: 0,      
        },
        initialize: function(options){
            this.ts_model = options.ts_model;
            this.order = options.order;
            
            this.selected = false;
        },
        
        set_selected: function(selected){
            this.selected = selected;
            this.trigger('change_line');
        },
        is_selected: function(){
            return this.selected;
        },
        check: function(){
            var res = true
            if ( this.get('product') == "" ) {
               res = false;
            }
            return res
        },
        get_product: function(){
            var product_obj = false
            if (this.check()){
                var product_name = this.get('product');
                var product_id = this.ts_model.db.product_name_id[product_name];
                var product_obj = this.ts_model.db.product_by_id[product_id]
            }
            return product_obj;
        },
        export_as_JSON: function() {

            return {
                qty: this.get('qty'),
                price_unit: this.get('pvp'),
                product_id:  this.ts_model.db.product_name_id[this.get('product')],
                product_uom: this.ts_model.db.unit_name_id[this.get('unit')],
                tax_ids: this.get('taxes_ids'),
                pvp_ref: this.get('pvp_ref'),
            };
        },
        get_price_without_tax: function(){
            return this.get_all_prices().priceWithoutTax;
        },
        get_price_with_tax: function(){
            return this.get_all_prices().priceWithTax;
        },
        get_tax: function(){
            return this.get_all_prices().tax;
        },
        get_all_prices: function(){
            var self = this;
            // var currency_rounding = this.pos.get('currency').rounding;
            // var currency_rounding = 0.01;
            var base = round_dc(this.get('qty') * this.get('pvp'), 2);
            var totalTax = base;
            var totalNoTax = base;
            var taxtotal = 0;
            // var product_list = this.pos.get('product_list');
            // debugger;
            var product =  this.get_product();

            if (product){ 
                
                var taxes_ids = self.get('taxes_ids')
                var taxes =  self.ts_model.get('taxes');
                var tmp;
                    var taxtotal;
                    var totalTax;
                _.each(taxes_ids, function(el) {
                    var tax = _.detect(taxes, function(t) {return t.id === el;});
                    
                    if (tax.price_include) {
                        if (tax.type === "percent") {
                            tmp =  base - round_dc(base / (1 + tax.amount),2); 
                        } else if (tax.type === "fixed") {
                            tmp = round_dc(tax.amount * self.get('qty'),2);
                        } else {
                            throw "This type of tax is not supported by the telesale system: " + tax.type;
                        }
                        tmp = round_dc(tmp,2);
                        taxtotal += tmp;
                        totalNoTax -= tmp;
                    } else {
                        if (tax.type === "percent") {
                            tmp = tax.amount * base;
                        } else if (tax.type === "fixed") {
                            tmp = tax.amount * self.get('qty');
                        } else {
                            throw "This type of tax is not supported by the telesale system: " + tax.type;
                        }
                        tmp = round_dc(tmp,2);
                        taxtotal += tmp;
                        totalTax += tmp;
                    }
                });
            }
            return {
                "priceWithTax": totalTax,
                "priceWithoutTax": totalNoTax,
                "tax": taxtotal,
            };
        },
        update_pvp: function(){
            var self = this;
            var customer_id = this.ts_model.db.partner_name_id[this.order.get('partner')];
            var pricelist_id = (this.ts_model.db.get_partner_by_id(customer_id)).property_product_pricelist;
            var model = new instance.web.Model("product.pricelist");
            var product_id = this.ts_model.db.product_name_id[this.get('product')];
            var loaded = model.call("ts_get_product_pvp",[product_id,pricelist_id])
            .then(function(result){
                if (result[0])
                    self.set('pvp', result[0])
                    self.set('total', my_round(self.get('qty') * result[0]),2);
            })
            return loaded;
        }
        
    });
    module.OrderlineCollection = Backbone.Collection.extend({
        model: module.Orderline,
    });


// **************************** ORDER AND ORDER COLLECTION***********************************************
    counter = 0;
    module.Order = Backbone.Model.extend({
        initialize: function(attributes){
            Backbone.Model.prototype.initialize.apply(this, arguments);
            this.set({
                creationDate:   new Date(),
                orderLines:     new module.OrderlineCollection(),
                name:           this.generateUniqueId(),
                //order #toppart values
                num_order: this.generateNumOrder(),
                partner_code: '',
                partner: '',
                contact_name: '',
                date_order: this.getStrDate(),
                date_invoice: '',
                limit_credit: '',
                customer_debt: '',
                //order #bottompart values
                total_boxes: (0).toFixed(2),
                total_weight: (0).toFixed(2),
                total_discount: (0).toFixed(2),
                total_discount_per: (0).toFixed(2)+" %",
                total_margin_per: (0).toFixed(2)+" %",
                total: (0).toFixed(2),
                total_base: (0).toFixed(2),
                total_iva: (0).toFixed(2),
                total_margin: (0).toFixed(2),
                total_fresh: (0).toFixed(2),
                selected_line: null,
                //to pas the button action to the server
                action_button: null,
                //to check save confirm cancel butons
                erp_id: false,
                erp_state: false,
                state:"new",
                comercial: '',
                coment: '',
            });
            
            this.ts_model =     attributes.ts_model; 
            this.selected_orderline = undefined;
            this.screen_data = {};  // see ScreenSelector
            return this;
        },
        generateNumOrder: function(){
            counter += 1;
            return "TStmp"+counter

        },
        getStrDate: function() {
            var date = new Date();
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            if (month < 10) month = "0" + month;
            if (day < 10) day = "0" + day;

            var today = year + "-" + month + "-" + day;
            return today;  
        },
        dateToStr: function(date) {
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            if (month < 10) month = "0" + month;
            if (day < 10) day = "0" + day;

            var today = year + "-" + month + "-" + day;
            return today;
        },
        generateUniqueId: function() {
            return new Date().getTime();
        },
        addLine: function() {
            var line = new module.Orderline({ts_model: this.ts_model, order:this})
            this.get('orderLines').add(line);
            return line
        },
        getSelectedLine: function(){
            var order_lines = this.get('orderLines').models;
            var res = false
            for (key in order_lines){
                var line = order_lines[key];
                if (line.is_selected())
                    res = line;
            }
            return res
        },
        removeLine: function(){
            var index = 0;
            (this.get('orderLines')).each(_.bind( function(item) {
                if ( item.is_selected() ){
                    this.get('orderLines').remove(item)
                    index = item.get('n_line') - 1;
                }
            }, this));
            if ( !$.isEmptyObject( this.get('orderLines')) ){
                 if (index > 0)
                    index = index - 1;
                var new_line = this.get('orderLines').models[index]
                this.selectLine(new_line);
            }
           
        },
        selectLine: function(line){
            if(line){
                if (line !== this.selected_orderline){
                    if(this.selected_orderline) {
                        this.selected_orderline.set_selected(false);    
                    }
                    this.selected_orderline = line;
                    this.set('selected_line',   this.selected_orderline );
                    this.selected_orderline.set_selected(true);
                }
            }
            else{
              this.selected_orderline = undefined;  
            }
        },
        get_client_name: function(){
            var client = this.get('partner');
            return client ? client.name : "";
        },
        getLastOrderline: function(){
            return this.get('orderLines').at(this.get('orderLines').length -1);
        },
        check: function(){
            var res = true
            if ( this.get("partner") == "" ){
                alert(_t("Partner can not be empty."));
                res = false
            }
            if ( this.get("orderLines").length == 0 ){
                alert(_t("Order lines can not be empty."));
                res = false;
            } else{
                (this.get('orderLines')).each(_.bind( function(item) {
                    if ( !item.check() ){
                        alert(_t("Product can not be empty"));
                        res = false;
                    }
                }, this));
            }
            return res
        },
        exportAsJSON: function() {
            var orderLines;
            orderLines = [];
            (this.get('orderLines')).each(_.bind( function(item) {
                return orderLines.push(item.export_as_JSON());
            }, this));
            return {
                lines: orderLines,
                name: this.get('num_order'),
                partner_id: this.ts_model.db.partner_name_id[this.get('partner')],
                action_button: this.get('action_button'),
                erp_id: this.get('erp_id'),
                erp_state: this.get('erp_state'),
                date_invoice: this.get('date_invoice'),
                note: this.get('coment'),
            };
        },
        get_last_line_by: function(period, client_id){
            var date = new Date();
            var date_str;
            if (period == "month") {
                date.setDate(date.getDate() - 30);
                date_str = this.dateToStr(date);
            }else{ //period = year
                var year = date.getFullYear()
                date_str = year + "-" + "01" + "-" + "01";
            }
            // console.log(date_str);
            var self=this;
            var domain = [['order_id.partner_id', '=', client_id],['order_id.date_order', '>=', date_str],['order_id.state', 'in', ['progress', 'manual', 'done']]]
            console.log("AAAAAAAAAAAA")
            var loaded = self.ts_model.fetch('sale.order.line',
                                            ['product_id','product_uom','product_uom_qty','price_unit','price_subtotal','tax_id','pvp_ref','current_pvp'],
                                            domain
                                            )
                .then(function(order_lines){
                    // console.log(order_lines);
                    console.log("CCCCCCCCC")
                    self.add_lines_to_current_order(order_lines);
                })
            return loaded
        },
        add_lines_to_current_order: function(order_lines){
            this.get('orderLines').unbind();  //unbind to render all the lines once, then in OrderWideget we bind again
            for (key in order_lines){
                var line = order_lines[key];
                var prod_obj = this.ts_model.db.get_product_by_id(line.product_id[0]);
                current_olines = this.get('orderLines').models
                var product_exist = false;
                for (key2 in current_olines){
                    var o_line = current_olines[key2];
                    var line_product_id =  this.ts_model.db.product_name_id[o_line.get('product')];

                    if (line_product_id == prod_obj.id)
                        product_exist = true;
                }
                if (!product_exist){
                    var line_vals = {ts_model: this.ts_model, order:this,
                                     code:prod_obj.default_code || "" ,
                                     product:prod_obj.name,
                                     unit:prod_obj.uom_id[1] || line.product_uom[1], //current product unit
                                     qty:line.product_uom_qty, //order line qty
                                     pvp: my_round(line.current_pvp ? line.current_pvp : 0, 2), //current pvp
                                     total: my_round(line.current_pvp ? line.product_uom_qty * line.current_pvp : 0 ,2),
                                     // discount: my_round( ((line.pvp_ref == 0) ? 0: 1 - (line.price_unit / line.pvp_ref)), 2 ),
                                     discount: my_round( 0, 2 ),
                                     weight: my_round(line.product_uom_qty * prod_obj.weight,2),
                                     margin: my_round(( (line.current_pvp != 0 && prod_obj.product_class != "fresh") ? ( (line.current_pvp - prod_obj.cmc) / line.current_pvp)  : 0 ), 2),
                                     taxes_ids: line.tax_id || product_obj.taxes_id || [],
                                     pvp_ref: line.current_pvp ? line.current_pvp : 0, //#TODO CUIDADO PUEDE NO ESTAR BIEN
                                     boxes: this.ts_model.convert_units_to_boxes(this.ts_model.db.get_unit_by_id(prod_obj.uom_id[0]),prod_obj,line.product_uom_qty),
                                    }
                    var line = new module.Orderline(line_vals);
                    this.get('orderLines').add(line);
                }
            }

            // var new_order_lines = this.get('orderLines').models
            // for (key in new_order_lines){
            //     var new_line = new_order_lines[key];
            //     $.when(new_line.update_pvp())
            //     .done(function(){
            //         debugger;
            //     });
            // }
        },
        get_last_order_lines: function(client_id){
            var self=this;
            this.ready = $.Deferred(); // used to notify the GUI that the PosModel has loaded all resources
            var domain = [['partner_id', '=', client_id],['state', 'in', ['progress', 'manual', 'done']]]
            var loaded = self.ts_model.fetch_limited_ordered('sale.order',['id','name','order_line'], //name y order line no necesarias
                                                domain,1,['-id'])
                .then(function(order){
                    // console.log(order)
                    return self.ts_model.fetch('sale.order.line',
                                                ['product_id','product_uom','product_uom_qty','price_unit','price_subtotal','tax_id','pvp_ref','current_pvp'],
                                                [
                                                    ['order_id', '=', order.id],  
                                                 ]);
                }).then(function(order_lines){
                    // console.log(order_lines);
                    self.add_lines_to_current_order(order_lines);
                })
            return loaded
        },
        addProductLine: function(product_id){
            var self=this;
            var customer_id = this.ts_model.db.partner_name_id[this.get('partner')];
            if (customer_id){
                var kwargs = {context: new instance.web.CompoundContext({}),
                              partner_id: customer_id,
                             }
                var pricelist_id = (this.ts_model.db.get_partner_by_id(customer_id)).property_product_pricelist;
                var model = new instance.web.Model("sale.order.line");
                model.call("product_id_change",[[],pricelist_id,product_id],kwargs)
                    .then(function(result){
                        var product_obj = self.ts_model.db.get_product_by_id(product_id);
                        var line_vals = {ts_model: self.ts_model, order:self,
                             code:product_obj.default_code || "" ,
                             product:product_obj.name,
                             unit:product_obj.uom_id[1],
                             qty:1,
                             pvp: my_round(result.value.price_unit || 0,2), //TODO poner impuestos de producto o vacio
                             total: my_round(result.value.price_unit || 0,2), //TODO poner impuestos de producto o vacio
                             discount: 0,
                             weight: product_obj.weight || 0.0,
                             margin: my_round( (result.value.price_unit != 0 && product_obj.product_class != "fresh") ? ( (result.value.price_unit - product_obj.cmc) / result.value.price_unit) : 0 , 2),
                             taxes_ids: result.value.tax_id || [],
                             pvp_ref: my_round(result.value.price_unit || 0,2), //TODO poner impuestos de producto o vacio
                             //TODO boxes
                            }
                        // debugger;
                        var line = new module.Orderline(line_vals);
                        self.get('orderLines').add(line);
                    });
            }
            else{
                alert(_t("No Customer defined in current order"));
            }
            
            var pricelist_id = (this.ts_model.db.get_partner_by_id(partner_id)).property_product_pricelist;
        },

    });

    module.OrderCollection = Backbone.Collection.extend({
        model: module.Order,
    });

    //**************************** CALLS AND CALLS COLLECTION****************************************************
    module.Calls = Backbone.Model.extend({
    });
    
    module.CallsCollection = Backbone.Collection.extend({
        model: module.Calls,
    });
}