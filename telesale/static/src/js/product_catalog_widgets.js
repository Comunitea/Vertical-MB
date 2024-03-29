/* mousetrap v1.4.6 craig.is/killing/mice */
function openerp_ts_product_catalog_widgets(instance, module){ //module is instance.point_of_sale
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

    module.ProductLineWidget = module.TsBaseWidget.extend({
        template:'Product-Line-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.product = options.product;
        },
        show_product_info: function() {
            var product_id = this.product.id
            if (product_id){
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: "product.product",
                    res_id: product_id,
                    views: [[false, 'form']],
                    target: 'new',
                    context: {},
                });
            }
        },
        add_product_to_order: function() {
            // this.ts_model.get('orders').add(new module.Order({ ts_model: self.ts_model, contact_name: 'aaa' }));
            // var self=this;
            var product_id = this.product.id
            if (product_id){
                var current_order= this.ts_model.get('selectedOrder')
                current_order.addProductLine(product_id);
                // this.ts_widget.screen_selector.set_current_screen('new_order');
                $('button#button_no').click();
                // current_order.selectLine(current_order.get('orderLines').last());
            }
        },
        renderElement: function() {
            var self=this;
            this._super();
            this.$('.show-product').click(_.bind(this.show_product_info, this));
            this.$('.add-product').click(_.bind(this.add_product_to_order, this));
        },
    });

    module.ProductCatalogWidget = module.TsBaseWidget.extend({
        template:'Product-Catalog-Widget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            /*this.ts_model.get('products').bind('reset', function(){
                self.renderElement();
            });*/
            this.ts_model.bind('change:update_catalog', function(){
                self.renderElement();
            });
            this.ts_model.bind('change:selectedOrder', this.change_selected_order, this);
            this.order_model = this.ts_model.get('selectedOrder');
            this.line_widgets = [];
            this.bind_order_events(); // SET this.order_model = this.ts_model.get('selectedOrder') and his widgets
        },
        bind_order_events: function(){
            console.log("No se muy bien para qwue linko el disparo al partner, no debería")
            this.order_model.bind('change:partner', this.search_products_to_sell, this);
        },
        search_products_to_sell: function(){

            var self = this;
            var search_string = ""
            var customer_name = this.order_model.get('partner');
            var products_list = [];
             var loaded = $.Deferred()
             var partner_id = this.ts_model.db.partner_name_id[customer_name];
             console.log("1.BUSCO PRODUCTOS")
             if (partner_id) {
                 var model = new instance.web.Model('res.partner');
                 model.call("search_products_to_sell",[partner_id])  //TODO revisar:devuelve ids que no estan activos (proceso de baja)
                 .then(function(result){
                     console.log("2.ENCUENTRO PRODUCTOS")
                     console.log(result)
                     self.ts_model.set('products_names', [])
                     self.ts_model.set('products_codes', [])
                     for (key in result){
                         var product_obj = self.ts_model.db.get_product_by_id(result[key])
                         if (product_obj){
                             products_list.push(product_obj);
                             search_string += self.ts_model.db._product_search_string(product_obj)
                             self.ts_model.get('products_names').push(product_obj.name);
                             self.ts_model.get('products_codes').push(product_obj.default_code);
                         }

                     }
                     self.ts_model.set('product_search_string', search_string)
                     self.ts_model.get('products').reset(products_list)
                     loaded.resolve()
                 });
             return loaded
             }
//            self.ts_model.set('products_names', [])
//            self.ts_model.set('products_codes', [])
//            for(id in self.ts_model.db.product_by_id){
//               var product_obj = self.ts_model.db.get_product_by_id(id)
//               if(product_obj){
//                   products_list.push(product_obj);
//                   search_string += self.ts_model.db._product_search_string(product_obj)
//                   self.ts_model.get('products_names').push(product_obj.name);
//                   self.ts_model.get('products_codes').push(product_obj.default_code);
//               }
//            }
//            self.ts_model.set('product_search_string', search_string)
//            self.ts_model.get('products').reset(products_list)
        },
        change_selected_order: function() {
            console.log('Se dispara el cambio de pedido seleccionado')
            this.order_model.unbind('change:partner');
            this.order_model = this.ts_model.get('selectedOrder');
            this.bind_order_events();
            this.search_products_to_sell();
        },
        renderElement: function () {
            var self = this;
            this._super();
            // free subwidgets  memory from previous renders
            for(var i = 0, len = this.line_widgets.length; i < len; i++){
                this.line_widgets[i].destroy();
            }
            this.line_widgets = [];
            var products = this.ts_model.get("products").models || [];
            my_len = products.length;
            if (my_len > 20){
                my_len = 20
            }
            for (var i = 0, len = my_len; i < len; i++){
                var product_obj = products[i].attributes;
                var product_line = new module.ProductLineWidget(self, {product: product_obj})
                this.line_widgets.push(product_line);
                product_line.appendTo(self.$('.productlines'));
            }
        },
    });
}
