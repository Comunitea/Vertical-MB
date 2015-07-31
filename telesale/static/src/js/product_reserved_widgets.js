/* mousetrap v1.4.6 craig.is/killing/mice */
function openerp_ts_product_reserved_widgets(instance, module){ //module is instance.point_of_sale
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

// **************************************************************************************************************************
// ********************************************PRODUCT RESERVED WIDGETS*********************************************************
// **************************************************************************************************************************

    module.ReservedlineWidget = module.TsBaseWidget.extend({
        template:'Reserved-Line-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.reserve = options.reserve;
        },
        renderElement: function() {
            var self=this;
            this._super();

            this.$("#button-create-reserve").off("click").click(_.bind(this.open_popup, this))
        },
        open_popup: function(parent, options){
            var self=this;
            self.ts_widget.screen_selector.show_popup('create_reserve_popup', self.reserve);
        },
    });


    module.ProductReservedWidget = module.TsBaseWidget.extend({
        template:'Product-Reserved-Widget',
        init: function(parent, options) {
            this._super(parent,options);
            this.product_reserves = [];

        },
        renderElement: function () {
            var self = this;
            this._super();
            this.$('#input-customer').autocomplete({
                source: this.ts_model.get('customer_names'),
            });
            this.$('#input-product').autocomplete({
                source: this.ts_model.get('products_names'),
            });
            this.$('#search-reserved').click(function (){ self.searchReserved() });

            var $reserved_lines = this.$('.reservedlines');
            for (key in this.product_reserves){
                var product_reserved = this.product_reserves[key];
                var reserved_line = new module.ReservedlineWidget(this, {reserve: product_reserved});
                reserved_line.appendTo($reserved_lines);
            }
        },
        searchReserved: function () {
            var self=this;
            var partner_name = this.$('#input-customer').val();
            var product_name = this.$('#input-product').val();
            var partner_id = this.ts_model.db.partner_name_id[partner_name];
            if (!partner_id){
                partner_id = false
            }
            var product_id = this.ts_model.db.product_name_id[product_name];
            if (!product_id){
                product_id = false
            }
            $.when(this.load_reserves(partner_id,product_id))
            .done(function(){
                self.renderElement();
                self.$('#input-customer').val(partner_name);
            }).fail(function(){
                //?????
            });
        },
        load_reserves: function(partner_id,product_id){
            var self=this;
            var domain =   []
            if (partner_id){
                domain.push(['partner_id2', '=', partner_id])
            }
            if (product_id){
                domain.push(['product_id', '=', product_id])
            }
            var loaded = self.ts_model.fetch('stock.reservation',
                                            ['partner_id2','product_id','product_uom_qty','product_uos_qty','served_Qty',
                                             'pending_qty', 'served_qty', 'state', 'invoice_state', 'min_unit'],
                                             domain)
                .then(function(reserves){
                    self.product_reserves = reserves;
                 })

            return loaded;
        },

    });

    /* POP UP FOR CREATE RESERVES*/
    module.CreateReservePopupWidget = module.PopUpWidget.extend({
        template: 'Create-Reserve-Pop-Up-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
            this.reserve = undefined
        },
        show: function(reserve){
            var self = this;
            this.reserve = reserve
            this._super();
             this.$('#create-reserve').off('click').click(function(){
                  if (self.check_fields()){
                    self.create_reserve();
                }
            })
            this.$('#close-reserve-popup').off('click').click(function(){

                self.ts_widget.screen_selector.close_popup('create_reserve_popup');
            })
        },
        check_fields: function(){
            var res = true;
            var ordered_qty = this.$('#ordered-qty').val()*1
            var customer = this.$('#customer-create').val()
            var comment = this.$('#comment-create').val()
            partner_id = this.ts_model.db.partner_name_id[customer];
            //TODO check date
            if (ordered_qty == 0){
                alert(_t("Not enought reserved quantity"));
                res = false;
            }
            if (ordered_qty > this.reserve.pending_qty){
                alert(_t("Not enought reserved quantity"));
                res = false;
            }

            return res
        },
        create_reserve: function(){
            var self=this;
            var model = new instance.web.Model("stock.reservation");
            var ordered_qty = this.$('#ordered-qty').val()*1
            model.call("create_reserve_from_ui",[this.reserve.id, ordered_qty],{context:new instance.web.CompoundContext()})
                .then(function(){
                    alert("Reserved Sale Created")
                    self.ts_widget.screen_selector.close_popup('create_reserve_popup');
                })
        },
    });
}
