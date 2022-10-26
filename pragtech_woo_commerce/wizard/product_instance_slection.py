from odoo import models, api, fields, _
from odoo.exceptions import UserError


class WooProductInstanceExp(models.Model):
    _name = 'woo.product.instance.exp'
    _description = 'Product Export Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_instance_selected_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['product.template'].export_selected_product(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductInstanceExp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(
                _("Please create and configure WooCommerce Instance"))
        if instance:
            res['woo_instance_id'] = instance.id
        return res


class WooProductInstanceImp(models.Model):
    _name = 'woo.product.instance.imp'
    _description = 'Product Import Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_instance_selected_for_imp(self):
        instance_id = self.woo_instance_id
        for _ in range(2):
            self.env['product.template'].import_product(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(
                _("Please create and configure WooCommerce Instance"))
        if instance:
            res['woo_instance_id'] = instance.id
        return res
