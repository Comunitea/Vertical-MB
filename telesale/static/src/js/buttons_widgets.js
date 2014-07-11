/* mousetrap v1.4.6 craig.is/killing/mice */
function openerp_ts_buttons(instance, module){ //module is instance.telesale
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

// ***********************************************************************************************************************************    
// ***********************************************************************************************************************************  
    
    module.SynchIconWidget = module.TsBaseWidget.extend({
        template: "Synch-Notification-Widget",
        init: function(parent, options){
            options = options || {};
            this._super(parent, options);
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$el.click(function(){
                self.ts_model.flush();
            });
        },
        start: function(){
            var self = this;
            this.ts_model.bind('change:nbr_pending_operations', function(){
                self.renderElement();
            });
        },
        get_nbr_pending: function(){
            return this.ts_model.get('nbr_pending_operations');
        },
    });

    //Generic Buttons whitch actions are part of TsWidget, like close button
    module.HeaderButtonWidget = module.TsBaseWidget.extend({
        template: 'HeaderButtonWidget',
        init: function(parent, options){
            options = options || {};
            this._super(parent, options);
            this.action = options.action;
            this.label   = options.label;

        },
        renderElement: function(){
            var self = this;
            this._super();
            if(this.action){
                this.$el.click(function(){ self.action(); });
            }
        },
        show: function(){ this.$el.show(); },
        hide: function(){ this.$el.hide(); },
    });

    // Class to change navigate buttons
    // module.ButtonBlockSelector = instance.web.Class.extend({
    //     init: function(options){
    //         this.block_set = options.block_set || {};
    //         this.default_button_block = options.default_button_block;
    //         this.current_block = null;
    //         this.current_block_name = null;
    //         for (block_name in this.block_set){
    //             this.block_set[block_name].hide();
    //         }
    //     },
    //     set_current_block: function(block_name){
    //         var new_block = this.block_set[block_name];
    //         if(!new_block){
    //             console.error("ERROR: set_current_block("+block_name+") : screen not found");
    //         }
    //         if (this.current_block){
    //             this.current_block.hide();
    //         }
    //         this.current_block = new_block;
    //         this.current_block_name = block_name;
    //         this.current_block.show();
    //     },
    //     set_default_block: function(){
    //         this.set_current_block(this.default_button_block);
    //     },
    // });


     module.ButtonBlockWidget = module.TsBaseWidget.extend({
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
            // (due to some events, or magic, or both...)  we must make sure they remain hidden.
            this._super();
            if(this.hidden){
                if(this.$el){
                    this.$el.hide();
                }
            }
        },
        select_screen: function(screen_name){
            var self = this;
            this.ts_widget.screen_selector.set_current_screen(screen_name);
        },
        select_button_block: function(block_name){
            var self = this;
            this.ts_widget.button_block_selector.set_current_block(block_name);
            // debugger;
            // if (this.$('.selected-screen'))
            //      this.$('.selected-screen').removeClass('selected-screen');
            // this.$el.addClass('selected-screen');
        },
        // close: function(){

        // },
    });

    // Buttons block to change between principal screens
    module.ScreenButtonWidget = module.ButtonBlockWidget.extend({
        template: 'ScreenButtonWidget',
        init: function(parent,options){
            this._super(parent,options);
            this.button1 = _t("New Order");
            this.button2 = _t("Summary Orders");
            this.button3 = _t("Call List");
            // this.button4 = _t("Telemarketer Analysis");
            // this.button5 = _t("Back");
            // this.button6 = _t("New Order");
            this.button8 = _t("Product Catalog");
            this.button9 = _t("Product Reserved");
            this.button7 = _t("Order History");
        },
        renderElement: function(){
            var self = this;
            this._super();
            // console.log("ScreenButtons Inicializado")
            this.$el.find('button#button1').click(function(){ self.select_screen('new_order');
                                                              // self.select_button_block('order_buttons');
                                                              self.setButtonSelected('button#button1');
                                                             });
            this.$el.find('button#button2').click(function(){ self.select_screen('summary_order');
                                                              self.setButtonSelected('button#button2');
                                                                 });
            this.$el.find('button#button3').click(function(){ self.select_screen('call_list');
                                                              self.setButtonSelected('button#button3');
                                                                 });
            // this.$el.find('button#button4').click(function(){ self.select_screen('tele_analysis');
            //                                                   self.setButtonSelected('button#button4');
            //                                                      });


            // this.$el.find('button#button5').click(function(){ 
            //                                                     // self.select_button_block('screen_buttons');
            //                                                   self.setButtonSelected('button#button5');
            //                                                  });
            // this.$el.find('button#button6').click(function(){ self.select_screen('new_order');
            //                                                   self.setButtonSelected('button#button6');
            //                                                  });
            this.$el.find('button#button7').click(function(){ self.select_screen('order_history')
                                                              self.setButtonSelected('button#button7');
                                                                ; });
            this.$el.find('button#button8').click(function(){ self.select_screen('product_catalog');
                                                              self.setButtonSelected('button#button8');
                                                             });
            this.$el.find('button#button9').click(function(){ self.select_screen('product_reserved');
                                                              self.setButtonSelected('button#button9');
                                                             });
           

        },
        setButtonSelected: function(button_selector) {
            $('.selected-screen').removeClass('selected-screen');
            $(button_selector).addClass('selected-screen');
        },
        

    });
    
    // New order buttons
    // module.OrderButtonBlockWidget = module.ButtonBlockWidget.extend({
    //     template: 'New_Order_Buttons_Widget',
    //     init: function(parent,options){
    //         this._super(parent,options)
    //         // console.log("init")
    //         this.button1 = _t("Back");
    //         this.button2 = _t("Order History");
    //         this.button3 = _t("Product Catalog");
    //         this.button4 = _t("Product Reserved");
    //         this.button5 = _t("Orders");
    //     },
    //     renderElement: function(){
    //         var self = this;
    //         this._super();
    //         // console.log("OrderButtons Inicializado")
    //         this.$el.find('button#button5').click(function(){ self.select_button_block('screen_buttons');
    //                                                           self.setButtonSelected('button#button5');
    //                                                          });
    //         this.$el.find('button#button7').click(function(){ self.select_screen('order_history')
    //                                                           self.setButtonSelected('button#button7');
    //                                                             ; });
    //         this.$el.find('button#button8').click(function(){ self.select_screen('product_catalog');
    //                                                           self.setButtonSelected('button#button8');
    //                                                          });
    //         this.$el.find('button#button9').click(function(){ self.select_screen('product_reserved');
    //                                                           self.setButtonSelected('button#button9');
    //                                                          });
    //         this.$el.find('button#button6').click(function(){ self.select_screen('new_order');
    //                                                           self.setButtonSelected('button#button6');
    //                                                          });

    //     },
    //     setButtonSelected: function(button_selector) {
    //         $('.selected-screen').removeClass('selected-screen');
    //         $(button_selector).addClass('selected-screen');
    //     },
    // });
}