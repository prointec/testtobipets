odoo.define('woo_graph_widget.graph', function (require) {
    "use strict";

    var fieldRegistry = require('web.field_registry');
    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var QWeb = core.qweb;

    var WooDashboardGraph = AbstractField.extend({
        className: "dashboard_graph_woo",
        events: {
            'change #sort_order_data': '_sortOrders',
            'click #instance_product': '_SyncedProducts',
            'click #instance_customer': '_SyncedCustomers',
            'click #instance_tax': '_SyncedTaxes',
            'click #instance_category': '_SyncedCategories',
            'click #instance_attribute': '_SyncedAttributes',
            'click #instance_order': '_SyncedOrders',
        },
        jsLibs: [
            '/web/static/lib/Chart/Chart.js',
        ],
        init: function () {
            this._super.apply(this, arguments);
            this.graph_type = this.attrs.graph_type;
            this.data = this.recordData
            this.match_key = _.find(_.keys(this.data), function(key){ return key.includes('_') })
            this.graph_data = this.match_key.length ? JSON.parse(this.data[this.match_key]) : {}

            this.context = this.record.context
        },

        on_attach_callback: function () {
            this._isInDOM = true;
            this._renderInDOM();
        },

        on_detach_callback: function () {
            this._isInDOM = false;
        },

        _render: function () {
            if (this._isInDOM) {
                return this._renderInDOM();
            }
            return Promise.resolve();
        },

        _renderInDOM: function () {
            this.$el.empty();
            this.$canvas = $('<canvas/>');
            this.$el.addClass(cssClass);
            this.$el.empty();
            if(this.graph_data){
                var dashboard = $(QWeb.render('woo_graph_dashboard_widget',{widget: this}))
                this.$el.append(dashboard);
                this.$el.find('.woo_graph').append(this.$canvas);
            } else {
                this.$el.append(this.$canvas);
            }
            var config, cssClass;
            var context = this.$canvas[0].getContext('2d');
            if (this.graph_type === 'bar') {
                config = this._getBarChartConfig(context);
                cssClass = 'o_graph_barchart';
            }
            this.chart = new Chart(context, config);
        },

        _getBarChartConfig: function (context) {
            if(!_.isEmpty(this.graph_data) && this.graph_data.hasOwnProperty('values')){
                var labels = this.graph_data.values.map(function (pt) {
                    return pt.x;
                });
                var borderColor = this.graph_data.is_sample_data ? '#0068ff' : '#0068ff';

                var gradientColor = context.createLinearGradient(0, 0, 0, 450);
                gradientColor.addColorStop(0.10, 'rgba(255, 87, 51, 0.25)');
                gradientColor.addColorStop(0.25, 'rgba(255, 255, 255, 0.25)');
                if(gradientColor){
                    var backgroundColor = gradientColor
                }
                else{
                    var backgroundColor = this.graph_data.is_sample_data ? '#ebebeb' : '#dcd0d9';
                }
                return {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: this.graph_data.values,
                            fill: 'start',
                            label: this.graph_data.key,
                            backgroundColor: '#2ecc71',
                            borderColor: '#27ae60',
                            borderWidth: 2,
                            pointStyle: 'bar',
                        }]
                    },
                    options: {
                        legend: {display: false},
                        scales: {
                            xAxes: [{
                                position: 'bottom'
                            }],
                            yAxes: [{
                                position: 'left',
                                ticks: {
                                    beginAtZero: true
                                },
                            }]
                        },
                        maintainAspectRatio: false,
                        elements: {
                            line: {
                                tension: 0.5,
                            }
                        },
                        tooltips: {
                            intersect: false,
                            position: 'nearest',
                            caretSize: 0,
                        },
                    },
                };
            }
        },

        _sortOrders: function (e) {
          var self = this;
          this.context.sort = e.currentTarget.value
            return this._rpc({model: self.model,method: 'read',args:[this.res_id],'context':this.context}).then(function (result) {
                if(result.length) {
                    self.graph_data = JSON.parse(result[0][self.match_key])
                    self.on_attach_callback()
                }
            })
        },

        _SyncedProducts: function () {
            return this.do_action(this.graph_data.product_data.product_action)
        },

        _SyncedCustomers: function () {
            return this.do_action(this.graph_data.customer_data.customer_action)
        },

        _SyncedOrders: function () {
            return this.do_action(this.graph_data.order_data.order_action)
        },

        _SyncedTaxes: function () {
            return this.do_action(this.graph_data.tax_data.tax_action)
        },

        _SyncedAttributes: function () {
             return this.do_action(this.graph_data.attribute_data.attribute_action)
        },

        _SyncedCategories: function () {
            return this.do_action(this.graph_data.category_data.category_action)
        },

        /*Render action for  shipped Order */
        _getShippedOrders: function () {
            return this.do_action(this.graph_data.order_shipped.order_action)
        },

        _getRefundOrders: function () {
            return this.do_action(this.graph_data.refund_data.refund_action)
        },

        _performOpration: function () {
            return this._rpc({model: this.model,method: 'perform_operation',args: [this.res_id]}).then( (result) => {
                this.do_action(result)
            });
        },

        _getReport: function () {
            return this._rpc({model: this.model,method: 'open_report',args: [this.res_id]}).then( (result) => {
                this.do_action(result)
            });
        },

        _getLog: function () {
         return this._rpc({model: this.model,method: 'open_logs',args: [this.res_id]}).then( (result) => {
                this.do_action(result)
            });
        },

    });

    fieldRegistry.add('dashboard_graph_woo', WooDashboardGraph);
    return {
        WooDashboardGraph: WooDashboardGraph
    };
});