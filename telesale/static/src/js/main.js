
openerp.telesale = function(instance) {
	
    instance.telesale = {};
    var module = instance.telesale;

    openerp_ts_db(instance,module);         // import db.js
    openerp_ts_models(instance,module);     // import models.js
    openerp_ts_basewidget(instance,module); // import ts_base_widgets.js
    openerp_ts_screens(instance,module);    // import screens.js
    openerp_ts_buttons(instance,module);    // import buttons.js
    openerp_ts_shortkeys(instance,module)   // import mousetrap library
    // openerp_ts_widgets(instance,module);    // import widgets.js
    openerp_ts_new_order_widgets(instance,module);    // import widgets.js
    openerp_ts_order_history_widgets(instance,module);    // import widgets.js
    openerp_ts_product_reserved_widgets(instance,module);    // import widgets.js
    openerp_ts_summary_orders_widgets(instance,module);    // import widgets.js
    openerp_ts_product_catalog_widgets(instance,module);    // import widgets.js
    openerp_ts_call_widgets(instance,module);    // import widgets.js

    instance.web.client_actions.add('ts.ui', 'instance.telesale.TsWidget');
};

    
