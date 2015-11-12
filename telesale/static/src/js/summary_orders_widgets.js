/* mousetrap v1.4.6 craig.is/killing/mice */
function openerp_ts_summary_orders_widgets(instance, module){ //module is instance.point_of_sale
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

// **************************************************************************************************************************
// ********************************************ORDER HISTORY WIDGETS*********************************************************
// **************************************************************************************************************************

   module.SummarylineWidget = module.TsBaseWidget.extend({
        template:'Summary-Line-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.order = options.order;
            this.open_order = undefined;
            this.order_fetch = undefined;
        },
        load_order_from_server: function(order_id, flag){
            var self=this;
            if (!flag){
                this.ts_model.get('orders').add(new module.Order({ ts_model: self.ts_model}));
            }
            this.open_order =  this.ts_model.get('selectedOrder')
            var loaded = self.ts_model.fetch('sale.order',
                                            ['supplier_id','contact_id','note','comercial','customer_comment','name','partner_id','date_order','state','amount_total','date_invoice', 'date_planned', 'date_invoice'],  //faltan los impuestos etc
                                            [
                                                ['id', '=', order_id],
                                                ['chanel', '=', 'telesale']
                                            ])
                .then(function(orders){
                    var order = orders[0];
                    self.order_fetch = order;
                    return self.ts_model.fetch('sale.order.line',
                                                ['product_id','product_uom','product_uom_qty','price_unit','product_uos', 'product_uos_qty','price_udv','price_subtotal','tax_id','pvp_ref','current_pvp','q_note', 'detail_note', 'discount'],
                                                [
                                                    ['order_id', '=', order_id],
                                                 ]);
                }).then(function(order_lines){
                     if (flag =='add_lines'){
                        self.open_order.add_lines_to_current_order(order_lines);
                        self.ts_widget.new_order_screen.data_order_widget.refresh();
                        self.ts_widget.new_order_screen.order_widget.change_selected_order()
                        self.ts_widget.new_order_screen.totals_order_widget.changeTotals();
                    }else{
                        self.ts_model.build_order(self.order_fetch, self.open_order, order_lines); //build de order model
                        self.ts_widget.new_order_screen.data_order_widget.refresh();  // show screen and order model refreshed.
                    }
                })
        },
        click_handler: function() {
            var self=this;
            $.when(self.load_order_from_server(self.order.id))
                .done(function(){
                    $('button#button_no').click();
                }).fail(function(){
                });
        },
        click_handler2: function() {
            var self=this;
            var order =  self.ts_model.get('selectedOrder')
            var partner_id = self.ts_model.db.partner_name_id[order.get('partner')]
            if (!partner_id){
                    alert(_t('Please select a customer before adding a order line'));
            }else{
            $.when(self.load_order_from_server(self.order.id, 'add_lines'))
                .done(function(){
                    $('button#button_no').click();
                });
            }
        },
        renderElement: function() {
            var self=this;
            this._super();
            // this.$el.click(_.bind(this.click_handler, this));
            this.$("#button-show-order").click(_.bind(this.click_handler, this));
            this.$("#button-adding-lines").click(_.bind(this.click_handler2, this));
        },
    });

    module.SummaryOrderWidget = module.TsBaseWidget.extend({
        template:'Summary-Order-Widget',
        init: function(parent, options) {
            this._super(parent,options);
            this.partner_orders = [];

        },
        renderElement: function () {
            var self = this;
            this._super();
            this.$('#search-customer2').click(function (){ self.searchCustomerOrders() });
            this.$('#search-customer2-week').click(function (){ self.searchCustomerOrdersBy('week') });
            this.$('#search-customer2-month').click(function (){ self.searchCustomerOrdersBy('month') });
            this.$('#search-customer2-trimester').click(function (){ self.searchCustomerOrdersBy('trimester') });
            var $summary_content = this.$('.summary-lines');
            for (key in this.partner_orders){
                var summary_order = this.partner_orders[key];
                var summary_line = new module.SummarylineWidget(this, {order: summary_order});
                summary_line.appendTo($summary_content);
            }
        },
        load_partner_orders: function(date_start,date_end){
            var self=this;
            var domain =   [['create_uid', '=', this.ts_model.get('user').id],['chanel', '=', 'telesale']]
            if (date_start != ""){
                domain.push(['date_order', '>=', date_start])
            }
            if (date_end != ""){
                domain.push(['date_order', '<=', date_end])
            }
            var loaded = self.ts_model.fetch('sale.order',
                                            ['name','partner_id','date_order','state','amount_total','date_invoice', 'date_planned', 'date_invoice'],  //faltan los impuestos etc
                                            domain)
                .then(function(orders){
                self.partner_orders = orders;
                 })

            return loaded;
        },
        searchCustomerOrders: function () {
            var self=this;
            // var partner_name = this.$('#input-customer2').val();
            var date_start = this.$('#input-date_start2').val();
            var date_end = this.$('#input-date_end2').val();

                $.when(this.load_partner_orders(date_start,date_end))
                .done(function(){
                    self.renderElement();
                }).fail(function(){
                    //?????
                });
            // };
        },
         searchCustomerOrdersBy: function (period){
            var self=this;
            var start_date = new Date();
            var end_date_str = this.ts_model.getCurrentDateStr()
            if (period == 'week')
                start_date.setDate(start_date.getDate() - 30);
            else if (period == 'month')
                start_date.setDate(start_date.getDate() - 30);
            else if (period == 'trimester')
                start_date.setDate(start_date.getDate() - 90);
            var start_date_str = this.ts_model.dateToStr(start_date);

                $.when(this.load_partner_orders(start_date_str,end_date_str))
                .done(function(){
                    self.renderElement();
                }).fail(function(){
                    //?????
                });

        },
    });
}
