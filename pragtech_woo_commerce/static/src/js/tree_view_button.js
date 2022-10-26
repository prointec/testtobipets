odoo.define('your_module_name.tree_view_button', function (require){
    "use strict";

    var ajax = require('web.ajax');
    var ListController = require('web.ListController');

    var rpc = require('web.rpc')

    ListController.include({
        renderButtons: function($node) {
            this._super.apply(this, arguments);
            var self = this;
            if (this.$buttons) {
                  $(this.$buttons).find('.oe_customer_import_button').on('click', function() {
                    self.do_action('pragtech_woo_commerce.action_wizard_import_customer', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="customer_instance_for_imp"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
                  });

                $(this.$buttons).find('.oe_product_import_button').on('click', function() {
                    self.do_action('pragtech_woo_commerce.action_wizard_woo_import_product_instance', {
                        additional_context: {},
                }).then(function(){
                       $('button[name="product_instance_selected_for_imp"]').on('click', function(){
                           setTimeout(function(){
		                       window.location.reload();
                           },20000);
                       });
                    });
                });

                $(this.$buttons).find('.oe_product_categ_import_button').on('click', function() {
                    self.do_action('pragtech_woo_commerce.action_wizard_woo_import_product_category', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="product_categ_instance_for_imp"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
                });

                $(this.$buttons).find('.oe_tax_import_button').on('click', function() {
                    var d = self.do_action('pragtech_woo_commerce.action_wizard_import_tax', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="tax_instance_for_imp"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
                });

               $(this.$buttons).find('.oe_so_import_button').on('click', function() {
                    var d = self.do_action('pragtech_woo_commerce.action_wizard_import_sale_order', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="sale_order_instance_for_imp"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
               });

                $(this.$buttons).find('.oe_inventory_import_button').on('click', function() {
                    var d = self.do_action('pragtech_woo_commerce.action_wizard_woo_import_inventory', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="import_woo_inventory"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
                });

                $(this.$buttons).find('.oe_attribute_import_button').on('click', function() {
                    var d = self.do_action('pragtech_woo_commerce.action_wizard_woo_import_product_attribute', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="product_attr_instance_for_imp"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
                });

                 $(this.$buttons).find('.oe_attribute_term_import_button').on('click', function() {
                    var d = self.do_action('pragtech_woo_commerce.action_wizard_woo_import_product_attribute_value', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="product_attr_value_instance_for_imp"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
                 });

                 $(this.$buttons).find('.oe_tag_import_button').on('click', function() {
                    var d = self.do_action('pragtech_woo_commerce.action_wizard_import_product_tag', {
                        additional_context: {},
                    }).then(function(){
                           $('button[name="product_tag_instance_for_imp"]').on('click', function(){
                               setTimeout(function(){
                                   window.location.reload();
                               },1500);
                           });
                        });
                 });
            }
        },
    });
});