function openerp_ts_models(instance, module){
    var QWeb = instance.web.qweb;
    _t = instance.web._t;
    var round_pr = instance.web.round_precision
    var round_dc = instance.web.round_decimals
    var my_round = function(number, decimals){
        var n = number || 0;
        if (typeof n === "string"){
            n = n * 1;
        }
        return n.toFixed(decimals) * 1
    };
// ***************************** ********** BASE TELESALE MODEL ***********************************************

    // var round_di = instance.web.round_decimals;
    // var round_pr = instance.web.round_precision;

    // The TsModel contains the Telesale system representation of the backend.
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
            this.ready2 = $.Deferred(); // used to notify the GUI that thepromotion has writed in the server
            // this.flush_mutex = new $.Mutex();  // used to make sure the orders are sent to the server once at time
            this.db = new module.TS_LS();                       // a database used to store the products and categories
            this.db.clear('products','partners');
            this.ts_widget = attributes.ts_widget;
            this.set({
                'currency': {symbol: $, position: 'after'},
                'shop':                 null,
                'user':                 null,
                'company':              null,
                'orders':               new module.OrderCollection(),
                'products':             new module.ProductCollection(),
                'calls':                new module.CallsCollection(),
                'sold_lines':           new module.SoldLinesCollection(),
                'product_search_string': "",
                'products_names':            [], // Array of products names
                'products_codes':            [], // Array of products code
                'sust_products':            [], // Array of products sustitutes
                'taxes':                null,
                'ts_session':           null,
                'ts_config':            null,
                'units':                [], // Array of units
                'units_names':          [], // Array of units names
                'qnotes':                [], // Array of qualitative note
                'qnotes_names':          [], // Array of qualitative note names
                'routes_names':          [], // Array of route names
                'customer_names':          [], // Array of customer names
                'customer_codes':          [], // Array of customer refs
                'supplier_names':          [], // Array of supplier refs
                'pricelist':            null,
                'selectedOrder':        null,
                'nbr_pending_operations': 0,
                'visible_products': {},
                'call_id': false,
                'update_catalog': 'a',  //value to detect changes between a and b to update the catalog only when click in label
                'bo_id': 0 //it's a counter to assign to the buttons when you do click on '+'
            });

            this.get('orders').bind('remove', function(){ self.on_removed_order(); });

            // We fetch the backend data on the server asynchronously. this is done only when the TS user interface is launched,
            // Any change on this data made on the server is thus not reflected on the telesale system until it is relaunched.
            // when all the data has loaded, we compute some stuff, and declare the Ts ready to be used.
            $.when(this.load_server_data())
                .done(function(){
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
        // helper function to load data from the server
        fetch: function(model, fields, domain, ctx){
            this._load_progress = (this._load_progress || 0) + 0.05;
            this.ts_widget.loading_message(_t('Loading')+' '+model,this._load_progress);
            return new instance.web.Model(model).query(fields).filter(domain).context(ctx).all()
        },
         // helper function to load last_
        fetch_limited_ordered: function(model, fields, domain, limit, orderby, ctx){
            return new instance.web.Model(model).query(fields).filter(domain).limit(limit).order_by(orderby).context(ctx).first()
        },
        fetch_ordered: function(model, fields, domain, orderby, ctx){
            return new instance.web.Model(model).query(fields).filter(domain).order_by(orderby).context(ctx).all()
        },
        // loads all the needed data on the sever. returns a deferred indicating when all the data has loaded.
        load_server_data: function(){
            var self=this;

            var loaded = self.fetch('res.users',['name','company_id'],[['id', '=', this.session.uid]])
                .then(function(users){
                    self.set('user',users[0]);
                    console.time('Test performance company');
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
                    console.timeEnd('Test performance company');
                    self.set('company',companies[0]);
                    console.time('Test performance units');
                    return self.fetch('product.uom', ['name'], []);
                }).then(function(units){
                    console.timeEnd('Test performance units');
                    for (key in units){
                        self.get('units_names').push(units[key].name)
                    }

                    self.db.add_units(units);
                    console.time('Test performance products');
                    // return self.fetch(
                    //     'product.product',
                    //       ['name','product_class','list_price','standard_price','default_code','uom_id', 'box_discount', 'log_base_id', 'log_unit_id', 'log_box_id', 'base_use_sale', 'unit_use_sale', 'box_use_sale','virtual_stock_conservative','taxes_id', 'weight', 'kg_un', 'un_ca', 'ca_ma','ma_pa', 'products_substitute_ids', 'product_tmpl_id', 'max_discount', 'category_max_discount'],
                    //     [['sale_ok','=',true], ['state2', '=', 'registered']]
                    // );
                    var model = new instance.web.Model('product.product');
                    return model.call("load_products",[],{context:new instance.web.CompoundContext()});
                }).then(function(products){
                    console.timeEnd('Test performance products');
                    self.db.add_products(products);

                    console.time('Test performance customers');
                    return self.fetch('res.partner',['comercial','supplier_ids','indirect_customer','name','ref', 'property_account_position', 'property_product_pricelist', 'credit', 'credit_limit', 'child_ids', 'phone', 'type', 'user_id', 'state', 'comment'], [['customer','=',true], ['state2','=','registered']])

                    // Por culpa de los properties no es eficiente
                    // var model = new instance.web.Model('res.partner');
                    // return model.call("load_partners",[true],{context:new instance.web.CompoundContext()});
                }).then(function(customers){
                    console.timeEnd('Test performance customers');
                    for (key in customers){
                        // var customer_name = customers[key].comercial || customers[key].name
                        // var customer_name = customers[key].comercial + ' | ' + customers[key].name + ' | ' + customers[key].ref
                        var customer_name = self.getComplexName(customers[key]);
                        self.get('customer_names').push(customer_name);
                        self.get('customer_codes').push(customers[key].ref);
                    }
                    self.db.add_partners(customers);
                    console.time('Test performance suppliers');
                    return self.fetch('res.partner',['name'], [['supplier','=',true], ['customer_ids','!=',false]])
                }).then(function(suppliers){
                  console.timeEnd('Test performance suppliers');
                    self.db.add_suppliers(suppliers);

                    console.time('Test performance Taxes');
                    return self.fetch('account.tax', ['amount', 'price_include', 'type'], [['type_tax_use','=','sale']]);
                }).then(function(taxes) {
                    console.timeEnd('Test performance Taxes');
                    self.set('taxes', taxes);
                    self.db.add_taxes(taxes);
                    console.time('Test performance FP map');
                    return self.fetch('account.fiscal.position.tax', ['position_id', 'tax_src_id', 'tax_dest_id']);


                }).then(function(fposition_map) {
                    console.timeEnd('Test performance FP map');
                    self.db.add_taxes_map(fposition_map);
                    console.time('Test performance FP');
                    return self.fetch('account.fiscal.position', ['name', 'tax_ids']);
                }).then(function(fposition) {
                    console.timeEnd('Test performance FP');
                    self.db.add_fiscal_position(fposition);
                    console.time('Test performance qnote');
                    return self.fetch('qualitative.note', ['name', 'code']);
                }).then(function(qnotes) {
                    console.timeEnd('Test performance qnote');
                    for (key in qnotes){
                        self.get('qnotes_names').push(qnotes[key].code)
                    }
                    self.db.add_qnotes(qnotes);
                  return self.fetch('route', ['code'], [['type', '=', 'telesale']]);
                }).then(function(routes) {
                    console.timeEnd('Test performance routes');
                    for (key in routes){
                        self.get('routes_names').push(routes[key].code)
                    }
                    self.db.add_routes(routes);
                })
            return loaded;
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
            self.ready2 = $.Deferred();
            //try to push an order to the server
            // shadow : true is to prevent a spinner to appear in case of timeout
            (new instance.web.Model('sale.order')).call('create_order_from_ui',[[order]],{context:new instance.web.CompoundContext()})
                .fail(function(unused, event){
                    //don't show error popup if it fails
                    console.error('Failed to send order:',order);
                    self._flush(index+1);
                    self.ready2.reject()
                })
                .done(function(){
                    //remove from db if success
                    self.db.remove_order(order.id);
                    self._flush(index);
                    self.get('selectedOrder').destroy(); // remove order from UI
                    self.ready2.resolve()
                });
        },
        // build a order loaded from the server as order_obj the selected order_model
        build_order: function(order_obj, order_model, order_lines){
            var partner_obj = this.db.get_partner_by_id(order_obj.partner_id[0]);
            var cus_name = this.getComplexName(partner_obj);
            order_model.set('partner', cus_name);
            order_model.set('partner_code', partner_obj.ref || "");
            order_model.set('customer_debt', my_round(partner_obj.credit,2));
            order_model.set('limit_credit', my_round(partner_obj.credit_limit,2));
            order_model.set('erp_id', order_obj.id);
            order_model.set('erp_state', order_obj.state);
            var state = order_obj.state
            order_model.set('state', state);
            order_model.set('date_invoice', order_obj.date_invoice);
            var only_date = order_obj.date_planned.split(' ');
            if(only_date.length > 1){
              order_model.set('date_planned', only_date[0]);
            }else {
              order_model.set('date_planned', order_obj.date_planned);
            }
            // order_model.set('date_planned', order_obj.date_planned);
            order_model.set('num_order',order_obj.name);
            order_model.set('customer_comment',order_obj.customer_comment || '');
            order_model.set('client_order_ref',order_obj.client_order_ref || '');
            order_model.set('comercial',partner_obj.user_id[1]);
            order_model.set('coment',order_obj.note || '');

            var supplier_name = ''
            if (order_obj.supplier_id){
                supplier_name = this.db.get_supplier_by_id(order_obj.supplier_id[0]);
                if (!supplier_name){
                  supplier_name = ''
                }
            }
            order_model.set('supplier', supplier_name);

            var contact = this.db.get_partner_contact(order_obj.partner_id[0])
            order_model.set('contact_name',contact.name);

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
                                //  discount: my_round( ((line.pvp_ref == 0) ? 0: 1 - (line.price_unit / line.pvp_ref)), 2 ),
                                 discount: my_round(line.discount, 2) || 0.0,
                                 weight: my_round(prod_obj.weight * line.product_uom_qty,2),
                                 margin: my_round( ( (line.price_unit != 0 && prod_obj.product_class == "normal") ? ( (line.price_unit - prod_obj.standard_price) / line.price_unit) : 0 ), 2),
                                 taxes_ids: line.tax_id || prod_obj.taxes_id || [],
                                 pvp_ref: line.pvp_ref,
                                 qnote: line.q_note[1] || "",
                                 detail: line.detail_note || "",
                                 product_uos: line['product_uos'][1] || "",
                                 product_uos_qty: line['product_uos_qty'] || 0.0,
                                 price_udv: line['price_udv'] || 0.0
                                }
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
        get_calls_by_date_state: function(date, state, route){
            var self=this;
            if (!state){state = $('#state-select').val()}
            if (!date){date = $('#date-call-search').val()}
            if (!route){route = $('#route_search').val()}
            if(date == ""){
              var domain = [['partner_id', '!=', false]]
            }else{
              var domain = [['date', '>=', date + " 00:00:00"],['date', '<=', date + " 23:59:59"], ['partner_id', '!=', false]]
            }
            if (state){
                if (state != "any")
                    domain.push(['state','=',state])
            }
            if (route != "0"){
              domain.push(['route_id', '=', parseInt(route)])
            }
            var context = new instance.web.CompoundContext()
            self.fetch('crm.phonecall',['date','partner_id','name','partner_phone','state','duration','route_id'],domain,context)
            .then(function(calls){
                if (!$.isEmptyObject(calls)){

                    for (key in calls){
                        calls[key].date = self.parse_utc_to_str_date(calls[key].date); //set dates in browser timezone
                        calls[key].duration = self.parse_duration_watch_format(calls[key].duration); //set dates in browser timezone
                        calls[key].partner_phone = self.db.get_partner_contact(calls[key].partner_id[0]).phone|| "-" //set phone of contact
                        calls[key].contact_name = self.db.get_partner_contact(calls[key].partner_id[0]).name //add contact name to phone
                    }
                }
                self.get('calls').reset(calls);
            });

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
        getUTCDateStr: function() {
            var date = new Date();
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            var hours = date.getUTCHours();
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
        getCurrentDatePlannedStr: function() {
            var date = new Date();
            day = date.getDay()
            add_days = 1
            if (day === 5) add_days = 3
            if (day === 6) add_days = 2
            date.setDate(date.getDate() + add_days)
            var day = date.getDate();
            var month = date.getMonth() + 1;
            var year = date.getFullYear();
            if (month < 10) month = "0" + month;
            if (day < 10) day = "0" + day;

            var today = year + "-" + month + "-" + day;
            return today;
        },
        parse_str_date_to_utc: function(str_date){

            // Todo esto porque lo de abajo cambia el mes por el día, le cambiamos la fecha antes para obtener el resultado correcto
            // var str_date2 = instance.web.datetime_to_str(Date.parse(str_date)); //Se comenta porque intercambia day por month, puede que dependa de si estás en firefox o en chrome
            var str_date2 = str_date;
            var str_year = str_date2.split(" ")[0].split("-")[0]
            var str_month = str_date2.split(" ")[0].split("-")[1]
            var str_day = str_date2.split(" ")[0].split("-")[2]
            var new_str = str_year + "-" + str_month + "-" + str_day + " " + str_date2.split(" ")[1]
            return new_str
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
            if (date_time){
              var splited =  date_time.split(" ");
              var date_part =  splited[0].split('-');
              var hour_part =  splited[1];
              return date_part[2] + "-" +  date_part[1] + "-" + date_part[0] + " " + hour_part;
          }
        },
        getComplexName: function(partner_obj){
            var res = '';
            if (partner_obj){
              res = partner_obj.comercial + ' | ' + partner_obj.name + ' | ' + partner_obj.ref
            }
            return res;
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
            qnote: '',
            detail: '',
            qty: 1,
            pvp: 0,
            pvp_ref: 0, //in order to change the discount
            total: 0,
            product_uos: '',
            product_uos_qty: 0,
            price_uos_qty: 0,
            price_udv: 0,
            //to calc totals
            discount: 0,
            specific_discount: 0,
            weight: 0,
            margin: 0,
            taxes_ids: [],
            temperature: 0,
        },
        initialize: function(options){
            this.ts_model = options.ts_model;
            this.order = options.order;

            this.selected = false;
        },

        set_selected: function(selected){
            this.selected = selected;
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
            var product_id = this.ts_model.db.product_name_id[this.get('product')];
            var uom_id = this.ts_model.db.unit_name_id[this.get('unit')];
            var uos_id = this.ts_model.db.unit_name_id[this.get('product_uos')];
            var qnote_id = this.ts_model.db.qnote_name_id[this.get('qnote')];
            return {
                qty: this.get('qty'),
                product_uom: uom_id,
                product_uos_qty: this.get('product_uos_qty'),
                product_uos: uos_id,
                price_unit: this.get('pvp'),
                price_udv: this.get('price_udv'),
                product_id:  product_id,
                qnote: qnote_id,
                tax_ids: this.get('taxes_ids'),
                pvp_ref: this.get('pvp_ref'),
                detail_note: this.get('detail') || "",
                discount: this.get('discount') || 0.0
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
            // var base = round_dc(this.get('qty') * this.get('pvp') * (1 - (this.get('discount') / 100.0)), 2);
            var base = this.get('qty') * this.get('pvp') * (1 - (this.get('discount') / 100.0));
            var totalTax = base;
            var totalNoTax = base;
            var taxtotal = 0;
            var product =  this.get_product();

            if (product){

                var taxes_ids = self.get('taxes_ids')
                var taxes =  self.ts_model.get('taxes');
                var tmp;
                    // var taxtotal;
                    // var totalTax;
                _.each(taxes_ids, function(el) {
                    var tax = _.detect(taxes, function(t) {return t.id === el;});

                    if (tax.price_include) {
                        if (tax.type === "percent") {
                            tmp =  base - base / (1 + tax.amount);
                        } else if (tax.type === "fixed") {
                            tmp = tax.amount * self.get('qty');
                        } else {
                            throw "This type of tax is not supported by the telesale system: " + tax.type;
                        }
                        // tmp = round_dc(tmp,2);
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
                        // tmp = round_dc(tmp,2);
                        taxtotal += tmp;
                        totalTax += tmp;
                    }
                });
            }
            return {
                "priceWithTax": my_round(totalTax,2),
                "priceWithoutTax": my_round(totalNoTax,2),
                "tax": my_round(taxtotal,2),
            };
        },
        // update_pvp: function(){
        //     // No se tiene en cuenta descuento
        //     var self = this;
        //     var customer_id = this.ts_model.db.partner_name_id[this.order.get('partner')];
        //     var pricelist_id = (this.ts_model.db.get_partner_by_id(customer_id)).property_product_pricelist;
        //     var model = new instance.web.Model("product.pricelist");
        //     var product_id = this.ts_model.db.product_name_id[this.get('product')];
        //     var loaded = model.call("ts_get_product_pvp",[product_id,pricelist_id])
        //     .then(function(result){
        //         if (result[0])
        //             self.set('pvp', result[0])
        //             self.set('total', my_round(self.get('qty') * result[0]),2);
        //     })
        //     return loaded;
        // }

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
                supplier: '',
                customer_comment: '',
                client_order_ref: '',
                contact_name: '',
                date_order: this.getStrDate(),
                date_invoice: this.getStrDatePlanned(),
                date_planned: this.getStrDatePlanned(),
                limit_credit: (0),
                customer_debt: (0),
                //order #bottompart values
                total_boxes: (0),
                total_weight: (0),
                total_discount: (0),
                total_discount_per: (0).toFixed(2)+" %",
                total_margin_per: (0).toFixed(2)+" %",
                total: (0),
                total_base: (0),
                total_iva: (0),
                total_margin: (0),
                total_fresh: (0),
                selected_line: null,
                //to pas the button action to the server
                action_button: null,
                //to check save confirm cancel butons
                erp_id: false,
                erp_state: false,
                state:"draft",
                comercial: '',
                coment: '',
                set_promotion: false // if true in the server we create a promotion, and recover again the order
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
         getStrDatePlanned: function() {
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
                date_order: this.get('date_order'),
                date_planned: this.get('date_planned'),
                note: this.get('coment'),
                customer_comment: this.get('customer_comment'),
                client_order_ref: this.get('client_order_ref'),
                supplier_id : this.ts_model.db.supplier_from_name_to_id[this.get('supplier')],
                set_promotion: this.get('set_promotion')
            };
        },
        get_last_line_by: function(period, client_id){
          var model = new instance.web.Model('sale.order.line');
          var cache_sold_lines = self.ts_model.db.cache_sold_lines[client_id]
          if (cache_sold_lines && period == 'year'){
              self.ts_model.get('sold_lines').reset(cache_sold_lines)
          }
          else{
              var loaded = model.call("get_last_lines_by",[period, client_id],{context:new instance.web.CompoundContext()})
                  .then(function(order_lines){
                          if (!order_lines){
                            order_lines = []
                          }
                            // self.add_lines_to_current_order(order_lines);
                          if(period == 'year'){
                              self.ts_model.db.cache_sold_lines[client_id] = order_lines;
                          }
                          self.ts_model.get('sold_lines').reset(order_lines)
                  });
                return loaded
          }
        },
        add_lines_to_current_order: function(order_lines, fromsoldprodhistory){
            this.get('orderLines').unbind();  //unbind to render all the lines once, then in OrderWideget we bind again
            if(this.selected_orderline && this.selected_orderline.get('code') == "" && this.selected_orderline.get('product') == "" ){
              $('.remove-line-button').click()
            }
            for (key in order_lines){
                var line = order_lines[key];
                var prod_obj = this.ts_model.db.get_product_by_id(line.product_id[0]);
                if  (!prod_obj){
                  alert(_t('This product can not be loaded, becouse is not registerd'))
                  return
                }
                current_olines = this.get('orderLines').models
                // var product_exist = false;
                for (key2 in current_olines){
                    var o_line = current_olines[key2];
                    var line_product_id =  this.ts_model.db.product_name_id[o_line.get('product')];

                    // if (line_product_id == prod_obj.id)
                    //     product_exist = true;
                }

                // if (!product_exist){
                var l_qty = line.product_uom_qty
                if(fromsoldprodhistory){
                  l_qty = 1.0;
                }
                var line_vals = {ts_model: this.ts_model, order:this,
                                 code:prod_obj.default_code || "" ,
                                 product:prod_obj.name,
                                 unit:prod_obj.uom_id[1] || line.product_uom[1], //current product unit
                                 qty:my_round(l_qty), //order line qty
                                 pvp: my_round(line.current_pvp ? line.current_pvp : 0, 2), //current pvp
                                 total: my_round(line.current_pvp ? (line.product_uom_qty * line.current_pvp) * (1 - line.discount /100) : 0 ,2),
                                 discount: my_round( line.discount || 0.0, 2 ),
                                 weight: my_round(line.product_uom_qty * prod_obj.weight,2),
                                 margin: my_round(( (line.current_pvp != 0 && prod_obj.product_class == "normal") ? ( (line.current_pvp - prod_obj.standard_price) / line.current_pvp)  : 0 ), 2),
                                 taxes_ids: line.tax_id || product_obj.taxes_id || [],
                                 pvp_ref: line.current_pvp ? line.current_pvp : 0, //#TODO CUIDADO PUEDE NO ESTAR BIEN
                                 qnote: line['q_note'][1] || "",
                                 detail: line["detail_note"] || "",
                                 product_uos: line['product_uos'][1] || "",
                                 product_uos_qty: line['product_uos_qty'] || 0.0,
                                 price_udv: line['price_udv'] || 0.0
                                }
                var line = new module.Orderline(line_vals);
                this.get('orderLines').add(line);
                // }
                // else{
                //   alert(_t("This product is already in the order"));
                // }
            }
            $('.col-code').focus(); //si no, al añadir línea desde resumen de pedidos, no existe foco y si añade más líneas da error
        },
        deleteProductLine: function(id_line){
          var self=this;
          // self.get('orderLines')
        },
        addProductLine: function(product_id){
            var self=this;
            // var customer_id = this.ts_model.db.partner_name_id[this.get('partner')];
            if($('#partner').val()){
                if(this.selected_orderline.get('code') == "" && this.selected_orderline.get('product') == "" ){
                  $('.remove-line-button').click()
                }
                $('.add-line-button').click()
                var added_line = self.ts_model.get('selectedOrder').getLastOrderline();
                var lines_widgets = self.ts_model.ts_widget.new_order_screen.order_widget.orderlinewidgets
                lines_widgets[lines_widgets.length - 1].call_product_id_change(product_id)
            }
            else{
                alert(_t('Please select a customer before adding a order line'));
            }
            // if (customer_id){
            //     var kwargs = {context: new instance.web.CompoundContext({}),
            //                   partner_id: customer_id,
            //                  }
            //     var pricelist_id = (this.ts_model.db.get_partner_by_id(customer_id)).property_product_pricelist;
            //     var model = new instance.web.Model("sale.order.line");
            //     model.call("product_id_change_with_wh",[[],pricelist_id,product_id],kwargs)
            //         .then(function(result){
            //             var product_obj = self.ts_model.db.get_product_by_id(product_id);
            //             var line_vals = {ts_model: self.ts_model, order:self,
            //                  code:product_obj.default_code || "" ,
            //                  product:product_obj.name,
            //                  product_uos_qty:1,
            //                  product_uos:product_obj.uom_id[1],
            //                  product_uos:(result.value.product_uos) ? self.model.ts_model.db.unit_by_id[result.value.product_uos].name : product_obj.uom_id[1]);
            //                  price_udv: my_round(result.value.price_unit || 0, 2),
            //                  unit:product_obj.uom_id[1],
            //                  qty:1,
            //                  pvp: my_round(result.value.price_unit || 0,2), //TODO poner impuestos de producto o vacio
            //                  total: my_round(result.value.price_unit || 0,2), //TODO poner impuestos de producto o vacio
            //                  discount: 0,
            //                  weight: product_obj.weight || 0.0,
            //                  margin: my_round( (result.value.price_unit != 0 && product_obj.product_class == "normal") ? ( (result.value.price_unit - product_obj.standard_price) / result.value.price_unit) : 0 , 2),
            //                  taxes_ids: result.value.tax_id || [],
            //                  pvp_ref: my_round(result.value.price_unit || 0,2), //TODO poner impuestos de producto o vacio
            //                 }
            //             var line = new module.Orderline(line_vals);
            //             line.call_product_id_change(product_obj.id)
            //             self.get('orderLines').add(line);
            //         });
            // }
            // else{
            //     alert(_t("No Customer defined in current order"));
            // }

            // var pricelist_id = (this.ts_model.db.get_partner_by_id(partner_id)).property_product_pricelist;
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
    //**************************** SOLD LINES AND SOLD LINESCOLLECTION***********************************************
    module.SoldLines = Backbone.Model.extend({
    });

    module.SoldLinesCollection = Backbone.Collection.extend({
        model: module.SoldLines,
    });
}
