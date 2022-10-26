from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from woocommerce import API


class Taxes(models.Model):
    _inherit = 'account.tax'

    woo_id = fields.Char('WooCommerce Id')
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)

    def cron_export_account_tax(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['account.tax'].export_selected_taxes(rec)

    def export_selected_taxes(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['account.tax'].browse(selected_ids)
        all_records = self.env['account.tax'].search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records
        list = []
        for rec in records:
            list.append({
                "id": rec.woo_id,
                "name": rec.name,
                "rate": str(rec.amount),
            })
        if list:
            for data in list:
                if data.get('id') == False:
                    try:
                        wcapi.post("taxes", data).json()
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))
                else:
                    try:
                        wcapi.post("taxes/" + data.get('id'), data).json()
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))
        self.import_tax(instance_id)

    def cron_import_account_tax(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['account.tax'].import_tax(rec)

    def import_tax(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )

        url = "taxes"
        try:
            data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc'})
        except Exception as error:
            raise UserError(_("Please check your connection and try again"))
        parsed_data = data.json()

        if data.status_code == 200:
            parsed_data = data.json()
            if parsed_data:
                for ele in parsed_data:
                    dict_tax = {}
                    tax_record = self.env['account.tax'].search([('woo_id', '=', ele.get('id')),
                                                                 ('name', '=', ele.get('name'))], limit=1)
                    tax_record_without_woo_id = self.env['account.tax'].search(
                        [('woo_id', '=', False), ('name', '=', ele.get('name'))], limit=1)

                    dict_tax['woo_instance_id'] = instance_id.id
                    dict_tax['company_id'] = instance_id.woo_company_id.id
                    dict_tax['is_exported'] = True

                    if ele.get('id'):
                        dict_tax['woo_id'] = ele.get('id')
                    if ele.get('name'):
                        dict_tax['name'] = ele.get('name')
                    if ele.get('rate'):
                        dict_tax['amount'] = ele.get('rate')
                    if not tax_record and not tax_record_without_woo_id:
                        self.env['account.tax'].create(dict_tax)
                    if not tax_record and tax_record_without_woo_id:
                        tax_record_without_woo_id.write(dict_tax)
                    if tax_record:
                        tax_record.write(dict_tax)

        else:
            raise UserError(_("Something went wrong, Please Check the Connections"))
