from odoo import models, api, fields, _
from odoo.exceptions import UserError



class AccountTaxInstanceExp(models.Model):
    _name = 'account.tax.instance.exp'
    _description = 'Tax Export Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def tax_instance_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['account.tax'].export_selected_taxes(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(AccountTaxInstanceExp, self).default_get(fields)
        rec= self.env['woo.instance'].search([])
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(
                _("Please create and configure WooCommerce Instance"))
        if instance:
            res['woo_instance_id'] = instance.id
        return res

class TaxInstanceImp(models.Model):
    _name = 'account.tax.instance.imp'
    _description = 'Tax Import Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def tax_instance_for_imp(self):
        instance_id = self.woo_instance_id
        self.env['account.tax'].import_tax(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(TaxInstanceImp, self).default_get(fields)
        # instance = self.env['woo.instance'].search([])[0]
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(
                _("Please create and configure WooCommerce Instance"))
        if instance:
            res['woo_instance_id'] = instance.id
        return res
