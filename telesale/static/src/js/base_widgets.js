function openerp_ts_basewidget(instance, module){ //module is instance.point_of_sale
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

    module.TsBaseWidget = instance.web.Widget.extend({
        init:function(parent,options){
            this._super(parent);
            options = options || {}; //avoid options undefined
            this.ts_model = options.ts_model || (parent ? parent.ts_model : undefined)
            this.ts_widget = options.ts_widget || (parent ? parent.ts_widget : undefined);  // In order all child's can acces telesale widget
        },
        show: function(){
            this.$el.show();
        },
        hide: function(){
            this.$el.hide();
        },
    });

    //Principal widget of Telesale System, contains all screens widgets and screens
    module.TsWidget = module.TsBaseWidget.extend({
        template: 'TsWidget',
        init: function() {
            this._super(arguments[0],{});
            instance.web.blockUI(); 

            this.ts_model = new module.TsModel(this.session)
            this.ts_widget = this; //So that Tswidget's childs have ts_widget set automatically
        },

        start: function() {
            var self = this;
            return self.ts_model.ready.done(function(){
                // self.build_currency_template(); // LLamada no implementasda en el widget base
                self.renderElement();  //Contruye la plantilla????

                
                self.build_widgets(); // BUILD ALL WIDGETS AND CREENS WIDGETS
                // console.log("WIDGETS CARGADOS")

                // self.button_block_selector.set_default_block(); // set principal block of widgets
                self.screen_selector.set_default_screen(); // set principal screen
                instance.web.unblockUI();
                self.$('.loader').animate({opacity:0},1500,'swing',function(){self.$('.loader').hide();});
                self.add_shortkey_events();
                self.ts_model.get_calls_by_date_state(self.ts_model.getCurrentDateStr()); // get call list for current date
                // self.ts_model.get('selectedOrder').bind('change', self.$("#partner").focus(), self)
                self.$("#partner").focus();


            }).fail(function(){   // error when loading models data from the backend
                self.try_close();
            });
        },
        
        build_widgets: function() {
            var self = this;
            // --------  WIDGETS ---------
            this.notification = new module.SynchIconWidget(this,{});
            this.notification.appendTo(this.$('#topheader'));

            // Close button --> Close the session
            this.close_button = new module.HeaderButtonWidget(this,{
                label: _t('Close'),
                action: function(){ self.try_close(); },
            });
            this.close_button.appendTo(this.$('#topheader'));

            // Buttons navigation screens
            this.screen_buttons = new module.ScreenButtonWidget(this, {});
            this.screen_buttons.appendTo(this.$('#topheader'));

            // New order buttons
            // this.order_buttons = new module.OrderButtonBlockWidget(this, {});
            // this.order_buttons.appendTo(this.$('#topheader'));



             // --------  SCREEN WIDGETS ---------

            //New Order Screen (default)
            this.new_order_screen = new module.OrderScreenWidget(this, {});
            this.new_order_screen.appendTo(this.$('#content'));
            //Summary Orders Screen
            this.summary_order_screen = new module.SummaryOrderScreenWidget(this, {});
            this.summary_order_screen.appendTo(this.$('#content'));
            // Call List Screen
            this.call_list_screen = new module.CallListScreenWidget(this, {});
            this.call_list_screen.appendTo(this.$('#content'));
            //TeleMarket Analysis Screen
            this.tele_analysis_screen = new module.TeleAnalysisScreenWidget(this, {});
            this.tele_analysis_screen.appendTo(this.$('#content'));
            //Customer Data Analysis Screen
            this.product_reserved_screen = new module.ProductReservedScreenWidget(this, {});
            this.product_reserved_screen.appendTo(this.$('#content'));
            //Order History Data Analysis Screen
            this.order_history_screen = new module.OrderHistoryScreenWidget(this, {});
            this.order_history_screen.appendTo(this.$('#content'));
            //Product Catalog Data Analysis Screen
            this.product_catalog_screen = new module.ProductCatalogScreenWidget(this, {});
            this.product_catalog_screen.appendTo(this.$('#content'));
            //Product PopUp 
            this.product_sust_popup = new module.SustPopupWidget(this, {});
            this.product_sust_popup.appendTo(this.$('#content'));
            //Add Call PopUp 
            this.add_call_popup = new module.AddCallPopupWidget(this, {});
            this.add_call_popup.appendTo(this.$('#content'));

            // --------  BUTTON BLOCK SELECTOR ---------

            // this.button_block_selector = new module.ButtonBlockSelector({
            //     block_set:{
            //         'screen_buttons': this.screen_buttons,
            //         'order_buttons': this.order_buttons
            //     },
            //     default_button_block: 'order_buttons',
            // });
            // --------  SCREEN SELECTOR ---------

            this.screen_selector = new module.ScreenSelector({
                screen_set:{
                    'new_order': this.new_order_screen,
                    'summary_order': this.summary_order_screen,
                    'call_list': this.call_list_screen,
                    'tele_analysis': this.tele_analysis_screen,
                    'product_reserved': this.product_reserved_screen,
                    'order_history': this.order_history_screen,
                    'product_catalog': this.product_catalog_screen,
                },
                popup_set:{
                    'product_sust_popup': this.product_sust_popup,
                    'add_call_popup': this.add_call_popup,
                },
                default_client_screen: 'new_order',
            });
        },
        add_shortkey_events: function(){
            var self=this;
            // allow shortcuts in any field of the screen.
            Mousetrap.stopCallback = function () {
                return false;
            }
            // Mousetrap.bind('esc', function() {
            //     self.$(window).click();
            // });
            //Add line
            Mousetrap.bind('alt+a', function(e) {
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.add-line-button').click();
            });
            //Remove line
            Mousetrap.bind('alt+s', function(e) {
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.remove-line-button').click()
            });

            //change betwen button block
            Mousetrap.bind('alt+q', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#button1').click();  //new order screen
                self.$("#partner").focus(); 

            });
            Mousetrap.bind('alt+w', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#button7').click(); //Order history page
                self.$('#input-customer').focus();
                // self.$('#button2').click(); //Summary orders page
                // self.$("#input-date_start2").focus();
            });
            Mousetrap.bind('alt+e', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#button8').click(); //product catalog
                self.$('#search-product').focus();
            });
            Mousetrap.bind('alt+r', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#button9').click();  //product reserved page
            });
            Mousetrap.bind('alt+t', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#button3').click();//call list page
                self.$('#date-call-search').focus();
            });
            Mousetrap.bind('alt+y', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                 self.$('#button2').click(); //Summary orders page
                self.$("#input-date_start2").focus();
            });
            Mousetrap.bind('ctrl+u', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#ult-button').click();  //ULT button
            });
            Mousetrap.bind('ctrl+m', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#vum-button').click();  //VUM button
            });
            Mousetrap.bind('ctrl+a', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#via-button').click();  //VIA button
            });
            Mousetrap.bind('ctrl+p', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#promo-button').click();  //PROMOT button
            });
            Mousetrap.bind('ctrl+s', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#sust-button').click();  //SUST button
            });
            Mousetrap.bind('ctrl+i', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#info-button').click();  //INFO button
            });
            Mousetrap.bind('ctrl+q', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('#show-client').click();  //SHOW button
            });

            Mousetrap.bind('ctrl+alt+b', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.save-button').click();  //SAVE button
            });
            Mousetrap.bind('ctrl+alt+c', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.cancel-button').click();  //CANCEL button
            });
            Mousetrap.bind('ctrl+alt+enter', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.confirm-button').click();  //CONFIRM button
            });
            Mousetrap.bind('ctrl+down', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                var wgt_order = self.new_order_screen.order_widget;
                var order_lines_wgts = wgt_order.orderlinewidgets;
                if (!$.isEmptyObject(order_lines_wgts)){
                    var order_model = self.ts_model.get('selectedOrder');
                    var selected_line_model = order_model.getSelectedLine();
                    var index = 0;
                    if (selected_line_model){
                        var index = selected_line_model.get('n_line');
                    }
                    var cur_line = order_lines_wgts[index-1]
                    if (index == order_lines_wgts.length)
                        index = 0;
                    
                    var line_wgt = order_lines_wgts[index];
                    // if (!line_wgt.model.is_selected()){
                        // if (cur_line) cur_line.$('.mandatory').blur();
                        line_wgt.$el.click();
                        line_wgt.$('.col-code').focus();
                    // }
                }  
            });
            Mousetrap.bind('ctrl+up', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                var wgt_order = self.new_order_screen.order_widget;
                var order_lines_wgts = wgt_order.orderlinewidgets;
                if (!$.isEmptyObject(order_lines_wgts)){
                    var order_model = self.ts_model.get('selectedOrder');
                    var selected_line_model = order_model.getSelectedLine();
                    var index = 0;
                    if (selected_line_model){
                        var index = selected_line_model.get('n_line') - 2;
                    }
                    var cur_line = order_lines_wgts[index+1]
                    if (index == -1)
                        index = order_lines_wgts.length - 1;
                    var line_wgt = order_lines_wgts[index];
                    if (!line_wgt.model.is_selected()){
                        // if (cur_line) cur_line.$('.mandatory').blur()
                        line_wgt.$el.click();
                        line_wgt.$('.col-code').focus();
                    }
                }  
            });
            
            Mousetrap.bind('alt+p', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.neworder-button').click();  //new order
            });

            Mousetrap.bind('alt+o', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.removeorder-button').click();  //remove order
            });

            Mousetrap.bind('ctrl+left', function(e){
                $( document.activeElement ).blur();
                if (e.preventDefault) e.preventDefault();
                else e.returnValue = false;
                self.$('.selected-order button')[0].focus();
            });

        },
        // Close funnctions. Returns to start session client action of TS menu
        try_close: function() {
            var self = this;
            self.close();
        },
        close: function() {
            var self = this;
            // return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_client_ts_menu']], ['res_id']).pipe(
            //         _.bind(function(res) {
            //     return this.rpc('/web/action/load', {'action_id': res[0]['res_id']}).pipe(_.bind(function(result) {
            //         var action = result;
            //         action.context = _.extend(action.context || {}, {'cancel_action': {type: 'ir.actions.client', tag: 'reload'}});
            //         //self.destroy();
            //         this.do_action(action);
            //     }, this));
            // }, this));
            function close(){
                return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_client_ts_menu']], ['res_id']).pipe(function(res) {
                    window.location = '/web#action=' + res[0]['res_id'];
                });
            }
            var draft_order = _.find( self.ts_model.get('orders').models, function(order){
                return order.get('orderLines').length !== 0
            });
            if(draft_order){
                if (confirm(_t("Pending orders will be lost.\nAre you sure you want to leave this session?"))) {
                    return close();
                }
            }else{
                return close();
            }
        },
    });

}