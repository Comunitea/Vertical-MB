
// this file contains the screens definitions. Screens are the
// content of the right pane of the telesale system, containing the main functionalities.
// screens are contained in the TsWidget, in widgets.js
// all screens are present in the dom at all time, but only one is shown at the
// same time.
//
// transition between screens is made possible by the use of the screen_selector,
// which is responsible of hiding and showing the screens, as well as maintaining
// the state of the screens between different orders.
//
// all screens inherit from ScreenWidget. the only addition from the base widgets
// are show() and hide() which shows and hides the screen but are also used to
// bind and unbind actions on widgets and devices. The screen_selector guarantees
// that only one screen is shown at the same time and that show() is called after all
// hide()s

function openerp_ts_screens(instance, module) { //module is instance.point_of_sale
    var QWeb = instance.web.qweb,
    _t = instance.web._t;

    module.ScreenSelector = instance.web.Class.extend({
        init: function(options){
            // options is a dict with screens instances passed in build_widgets in TsWidget
            this.screen_set = options.screen_set || {};
            this.popup_set = options.popup_set || {};
            this.default_client_screen = options.default_client_screen;
            this.current_screen = null;
            this.current_popup = null;
            for(screen_name in this.screen_set){
                this.screen_set[screen_name].hide();
            }
            for(popup_name in this.popup_set){
                this.popup_set[popup_name].hide();
            }
        },
        set_current_screen: function(screen_name){
            var new_screen = this.screen_set[screen_name];
            if(!new_screen){
                console.error("ERROR: set_current_screen("+screen_name+") : screen not found");
            }
            if (this.current_screen){
                // this.current_screen.close()
                this.current_screen.hide();
            }
            this.current_screen = new_screen;
            this.current_screen.show();
        },
        set_default_screen: function(){
            this.set_current_screen(this.default_client_screen);
        },
        show_popup: function(name, extra_data){
            if(this.current_popup){
                this.close_popup();
            }
            this.current_popup = this.popup_set[name];
            if (name=="create_reserve_popup"){
                // extra data will be the reserve line widget
                this.current_popup.show(extra_data);
            }
            if (name=="finish_call_popup"){
                // extra data will be the call line widget
                this.current_popup.show(extra_data);
            }
            else{
                this.current_popup.show(extra_data);
            }
            this.current_screen.show();
        },
        close_popup: function(){
            if(this.current_popup){
                this.current_popup.close();
                this.current_popup.hide();
                this.current_popup = null;
            }
        },
    });

    module.ScreenWidget = module.TsBaseWidget.extend({
        init: function(parent,options){
            this._super(parent,options);
            this.hidden = false;
        },
        show: function(){
            var self = this;
            this.hidden = false;
            if(this.$el){
                this.$el.show();
            }
        },
        hide: function(){
            this.hidden = true;
            if (this.$el){
                this.$el.hide();
            }
        },
        renderElement: function(){
            // we need this because some screens re-render themselves when they are hidden
            // (due to some events, or magic, or both...) we must make sure they remain hidden.
            this._super();
            if(this.hidden){
                if(this.$el){
                    this.$el.hide();
                }
            }
        },
    });

    module.PopUpWidget = module.TsBaseWidget.extend({
        show: function(){
            if(this.$el){
                this.$el.show();
            }
        },
        /* called before hide, when a popup is closed */
        close: function(){
        },
        /* hides the popup. keep in mind that this is called in the initialization pass of the
         * pos instantiation, so you don't want to do anything fancy in here */
        hide: function(){
            if(this.$el){
                this.$el.hide();
            }
        },
    });


    module.OrderScreenWidget = module.ScreenWidget.extend({
        template: 'Order-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
            document.title = "Televenta"
        },
        start: function(){
            var self = this;
            this.$('.neworder-button').click(function(){
                self.ts_model.add_new_order();
            });

            this.$('.removeorder-button').click(function(){
                var r = confirm(_t("Do you want remove this order"));
                if (r)
                    self.ts_model.get('selectedOrder').destroy();
                // self.ts_model.get('orders').remove(self.ts_model.get('selectedOrder'));
            });

            //when a new order is created, add an order button widget.
            this.ts_model.get('orders').bind('add', function(new_order){
                var new_order_button = new module.OrderButtonWidget(null, {
                    order: new_order,
                    ts_model: self.ts_model
                });
                new_order_button.appendTo($('#orders'));
                new_order_button.selectOrder();
            }, self);
            // Also creates first order when is loaded for dirst time
            this.ts_model.get('orders').add(new module.Order({ ts_model: self.ts_model }));
            this.order_widget= new module.OrderWidget(this, {});
            this.order_widget.replace($('#placeholder-order-widget'));
            //top part
            this.data_order_widget = new module.DataOrderWidget(this, {});
            this.data_order_widget.replace($('#placeholder-toppart'));
            //bottom part
            this.totals_order_widget = new module.TotalsOrderWidget(this, {});
            this.totals_order_widget.replace($('#placeholder-bottompart'));
            //right part
            this.productinfo_order_widget = new module.ProductInfoOrderWidget(this, {});
            this.productinfo_order_widget.replace($('#placeholder-bottompart-left'));
            this.sold_product_line_widget = new module.SoldProductWidget(this, {});
            this.sold_product_line_widget.replace($('#placeholder-rightpart'));

        }
    });

    module.SummaryOrderScreenWidget = module.ScreenWidget.extend({
        template: 'Summary-Order-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        start: function(){
            this.summary_order_widget = new module.SummaryOrderWidget(this, {});
            this.summary_order_widget.replace($('#placeholder-summary-order-widget'));
        },
    });

    module.TeleAnalysisScreenWidget = module.ScreenWidget.extend({
        template: 'Tele-Analysis-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        }
    });

// ************************* NEW ORDER SCREENS ***************************************

    module.ProductReservedScreenWidget = module.ScreenWidget.extend({
        template: 'Product-Reserved-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        start: function(){
            this.product_reserved_widget = new module.ProductReservedWidget(this, {});
            this.product_reserved_widget.replace($('#placeholder-product-reserved-widget'));
        },
    });

    module.KeyShortsScreenWidget = module.ScreenWidget.extend({
        template: 'Key-Shorts-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        start: function(){

        },
    });

    module.OrderHistoryScreenWidget = module.ScreenWidget.extend({
        template: 'Order-History-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        start: function(){
            this.order_history_widget = new module.OrderHistoryWidget(this, {});
            this.order_history_widget.replace($('#placeholder-order-history-widget'));

        },
    });

    module.ProductCatalogScreenWidget = module.ScreenWidget.extend({
        template: 'Product-Catalog-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        search_customer_products: function(query,string){
            var re = RegExp("([0-9]+):.*?"+query,"gi");
            var results = [];
            for(var i = 0; i < 100; i++){
                r = re.exec(string);
                if(r){
                    var id = Number(r[1]);
                    results.push(this.ts_model.db.get_product_by_id(id));
                }else{
                    break;
                }
            }
            return results;
        },
        start: function(){
            var self = this;
            this.product_catalog_widget = new module.ProductCatalogWidget(this, {});
            this.product_catalog_widget.replace($('#placeholder-product-catalog-widget'));
            this.$("#search-product").keyup(function(event){
                var query = $(this).val().toLowerCase();
                if(query && self.ts_model.get("product_search_string")){
                    if(event.which === 13){
                        if( self.ts_model.get('products').size() === 1 ){
                            self.ts_model.get('selectedOrder').addProductLine(self.ts_model.get('products').at(0).id);
                            // self.clear_search();
                        }
                    }else{
                        var products = self.search_customer_products(query,self.ts_model.get("product_search_string"));
                        self.ts_model.get('products').reset(products);
                        var upd = self.ts_model.get('update_catalog')
                        if (upd === 'a'){
                            upd = 'b'
                        }
                        else{
                            upd = 'a'
                        }
                        self.ts_model.set('update_catalog', upd)
                        // self.$('.search-clear').fadeIn();
                    }
                }else{
                    // var products = self.ts_model.db.get_product_by_category(self.category.id);
                    // self.ts_model.get('products').reset(products);
                    // self.$('.search-clear').fadeOut();
                }
            });
        }
    });

    module.CallListScreenWidget = module.ScreenWidget.extend({
        template: 'Call-List-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        start: function(){
            var self = this;
            this.call_list_widget = new module.CallListWidget(this, {});
            this.call_list_widget.replace($('#placeholder-call-list-widget'));
            this.$("#date-call-search").blur(function(){
                var date = self.$('#date-call-search').val()
                self.ts_model.get_calls_by_date_state(date);
            });
            this.$("#state-select").change(function(){
                var date = self.$('#date-call-search').val()
                var state = self.$('#state-select').val()
                self.ts_model.get_calls_by_date_state(date,state);
            })
            this.$("#create-call").click(function(){
                state = self.$('#state-select').val()
                self.ts_widget.screen_selector.show_popup('add_call_popup', false);
            })

        },

    });

    module.SustPopupWidget = module.PopUpWidget.extend({
        template: 'Sust-Pop-Up-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        start: function(){
            var self = this;

        },
        show: function(){
            var self = this;
            this._super();
            if (!this.sust_widget){
                this.sust_widget = new module.ProductSustWidget(this, {});
                this.sust_widget.replace($('#placeholder-sust-widget'));
            }
            this.sust_widget.renderElement()

            this.$('#close-sust').off('click').click(function(){
                self.ts_widget.screen_selector.close_popup('product_sust_popup');
            })
        },
    });
}
