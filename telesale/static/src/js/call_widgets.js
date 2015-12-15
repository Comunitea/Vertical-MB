/* mousetrap v1.4.6 craig.is/killing/mice */
function openerp_ts_call_widgets(instance, module){ //module is instance.point_of_sale
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

    module.CallLineWidget = module.TsBaseWidget.extend({
        template:'Call-Line-Widget',
        init: function(parent, options){
            this._super(parent,options);
            this.call = options.call;
        },
        renderElement: function() {
            var self=this;
            this._super();
            this.$('.save-call').off("click").click(_.bind(this.save_call, this));
            this.$('#do-call').off("click").click(_.bind(this.do_call, this));
            this.$('#finish-call').off("click").click(_.bind(this.finish_call_pop, this));
        },
        save_call: function(){
           this.ts_widget.screen_selector.show_popup('finish_call_popup', false);
        },
        create_order_from_call: function(){

            this.ts_model.add_new_order();
            var partner_id = this.call.partner_id[0]
            var partner_obj = this.ts_model.db.get_partner_by_id(partner_id);
            var order_model = this.ts_model.get('selectedOrder');
            var cus_name  = this.ts_model.getComplexName(partner_obj);
            order_model.set('partner', cus_name);
            order_model.set('partner_code', partner_obj.ref || "");
            order_model.set('limit_credit', my_round(partner_obj.credit_limit,2));
            order_model.set('customer_debt', my_round(partner_obj.credit, 2));
            order_model.set('customer_comment', partner_obj.comment);
            contact_obj = this.ts_model.db.get_partner_contact(partner_id); //If no contacts return itself
            order_model.set('contact_name', contact_obj.name);
            this.ts_widget.new_order_screen.data_order_widget.renderElement()
            $('button#button_no').click();
        },
        do_call: function(){
                var self=this;

                var call_id =Number(this.call.id);

                //obtenr momrnto de inicio y guardarlo psrs obtener duracción
                var model = new instance.web.Model("crm.phonecall");

                model.call("read",[call_id, ["state"]]).then(function(res){
                    if (res.state == "calling"){  // call already in course
                        alert(_t("This call is in course by another person"));
                    }
                    else if(res.state == "open"){  // set call on course
                        var model = new instance.web.Model("crm.phonecall");
                        var date_init = self.ts_model.parse_str_date_to_utc(self.ts_model.getUTCDateStr())  //set dat in UTC from write in correct GMT0 openerp
                        //set date to calculate duration from server
                        model.call("write",[[res.id], {'state': "calling", 'date': date_init}],{context:new instance.web.CompoundContext()}).then(function(result){
                            self.ts_model.set('call_id', call_id);  //set id of current call
                            self.create_order_from_call();
                            self.call.state = 'calling';
                            self.ts_widget.call_list_screen.call_list_widget.renderElement();
                        });
                    }else{
                        alert(_t("You can't do a call with state diferent to confirmed"));
                    }

                })
        },
        finish_call_pop: function(){
            var call_line=this
            this.ts_widget.screen_selector.show_popup('finish_call_popup', call_line);
        },
        finish_call: function(result_call){
            var self=this;
            var call_id =Number(this.call.id);
            result_code = result_call
            if (result_code){
                //obtenr fin y guardarlo psrs obtener duracción
                var model = new instance.web.Model("crm.phonecall");
                 model.call("write",[[call_id], {'result': result_code}],{context:new instance.web.CompoundContext()}).then(function(result){
                    self.ts_model.set('call_id', false);
                    // self.call.state = 'done';
                    var state = $('#state-select').val()
                    //var date = self.ts_model.getCurrentDateStr()
                    var date = $('#date-call-search').val()
                    self.ts_model.get_calls_by_date_state(date, state);
                    self.ts_widget.call_list_screen.call_list_widget.renderElement();
                    self.ts_widget.screen_selector.close_popup('add_call_popup');
                });
            }
            else{
                alert(_t("Not found a result code for result call of '" + result_call + "'"));
            }
        },
    });

     module.CallListWidget = module.TsBaseWidget.extend({
        template:'Call-List-Widget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.ts_model.get('calls').bind('reset', function(){
                self.renderElement();
            });
            this.line_widgets = [];

        },
        renderElement: function () {
            var self = this;
            this._super();

            // free subwidgets  memory from previous renders
            for(var i = 0, len = this.line_widgets.length; i < len; i++){
                this.line_widgets[i].destroy();
            }
            this.line_widgets = [];
            var calls = this.ts_model.get("calls").models || [];
            for (var i = 0, len = calls.length; i < len; i++){
                var call_obj = calls[i].attributes;
                var call_line = new module.CallLineWidget(self, {call: call_obj})
                this.line_widgets.push(call_line);
                call_line.appendTo(self.$('.calllines'));
            }
        },
    });

    /* POP UP FOR CREATE CALLS*/
    module.AddCallPopupWidget = module.PopUpWidget.extend({
        template: 'Add-Call-Pop-Up-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        show: function(){
            var self = this;
            this._super();

            var date_str = this.ts_model.getCurrentFullDateStr()
            var date_str = date_str.replace(" ","T")  // T because chrome widget date,
            this.$('#date-call-create').val(date_str) // Set current date and time
            this.$('#customer-create').val("") // Set current date and time
            this.$('#comment-create').val("") // Set current date and time
            this.$('#customer-create').autocomplete({
                source: self.ts_model.get('customer_names'),
            });
             this.$('#create-phonecall').off('click').click(function(){
                  if (self.check_fields()){
                    self.create_phonecall();
                }
            })
            this.$('#close-call-popup').off('click').click(function(){

                self.ts_widget.screen_selector.close_popup('add_call_popup');
            })
        },
        check_fields: function(){
            var res = true;
            var date = this.$('#date-call-create').val()
            var customer = this.$('#customer-create').val()
            var comment = this.$('#comment-create').val()
            partner_id = this.ts_model.db.partner_name_id[customer];
            //TODO check date
            if (!date){
                alert(_t("Date is empty. Please select one."));
                res = false;
            }
            else if (!partner_id){
                alert(_t("Customer name '" + customer + "' does not exist"));
                this.$('#customer-create').val("");
                res = false;
            }else if (!comment){
                alert(_t("Coment is a mandatory field"));
                res = false;
            }
            return res
        },
        create_phonecall: function(){
            var self=this;
            var date = (this.$('#date-call-create').val()).replace("T", " ");
            var customer = this.$('#customer-create').val()
            partner_id = this.ts_model.db.partner_name_id[customer];
            var comment = this.$('#comment-create').val()
            var model = new instance.web.Model("crm.phonecall");
            var date_create = self.ts_model.parse_str_date_to_utc(date)  //set dat in UTC from write in correct
            var vals = {
                'name': comment,
                'partner_id': partner_id,
                'date': date_create,
            }
            model.call("create",[vals],{context:new instance.web.CompoundContext()})
                .then(function(){
                    self.ts_model.get_calls_by_date_state(self.ts_model.getCurrentDateStr());
                    self.ts_widget.screen_selector.close_popup('add_call_popup');

                })
            this.$('#close-finish-call-popup').off('click').click();
        },
    });

    /* POP UP FOR FINISH CALLS*/
    module.FinishCallPopupWidget = module.PopUpWidget.extend({
        template: 'Finish-Call-Pop-Up-Screen-Widget',
        init: function(parent,options){
            this._super(parent,options)
        },
        show: function(call_line){
            var self = this;
            this._super();

             this.$('#finish-call').off('click').click(function(){
                result = self.$('#result_call').val() // Get result call
                call_line.finish_call(result)
            })
            this.$('#close-finish-call-popup').off('click').click(function(){

                self.ts_widget.screen_selector.close_popup('finish_call_popup');
            })
        },
    });
}
