from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from woocommerce import API


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    woo_id = fields.Char('WooCommerce Id')
    is_exported = fields.Boolean('Exported')
    slug = fields.Char('Slug')


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    woo_id = fields.Char('WooCommerce Id')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)
    slug = fields.Char('Slug')
    woo_instance_id = fields.Many2one('woo.instance')

    def cron_export_product_attr(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute'].export_selected_attribute(rec)

    def export_selected_attribute(self, instance_id):
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
        selected_records = self.env['product.attribute'].browse(selected_ids)
        all_records = self.env['product.attribute'].search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records
        list = []
        attr_val = []
        for rec in records:
            for val in rec.value_ids:
                attr_val.append({
                    'id': val.woo_id,
                    'name': val.name,
                    'slug': str(val.slug) if val.slug else '',
                    'description': str(val.description) if val.description else '',
                })

            list.append({
                'id': rec.woo_id,
                'name': rec.name,
                'slug': rec.slug if rec.slug else '',

            })
        if list:
            for data in list:
                if data.get('id') == False:
                    wcapi.post("products/attributes", data).json()
                else:
                    if attr_val:
                        for rec in attr_val:
                            if rec:
                                if rec.get('id'):
                                    try:
                                        wcapi.post("products/attributes/%s/terms/%s" % (data.get('id'), rec.get('id')), rec)
                                    except Exception as error:
                                        raise UserError(_("Please check your connection and try again"))
                                else:
                                    try:
                                        wcapi.post("products/attributes/%s/terms" % data.get('id'), rec).json()
                                    except Exception as error:
                                        raise UserError(_("Please check your connection and try again"))

                    wcapi.post("products/attributes/%s" % (data.get('id')), data).json()
        self.import_product_attribute(instance_id)

    def cron_import_product_attr(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute'].import_product_attribute(rec)

    def import_product_attribute(self, instance_id):

        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )
        url = "products/attributes"
        try:
            data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc'})
        except Exception as error:
            raise UserError(_("Please check your connection and try again"))
        if data.status_code == 200:
            parsed_data = data.json()
            if parsed_data:
                for ele in parsed_data:
                    dict_e = {}
                    attribute = self.env['product.attribute'].search([('woo_id', '=', ele.get('id')), ('name', '=', ele.get('name'))], limit=1)
                    attribute_without_woo = self.env['product.attribute'].search([('woo_id', '=', False), ('name', '=', ele.get('name'))], limit=1)

                    dict_e['woo_instance_id'] = instance_id.id
                    dict_e['is_exported'] = True
                    if ele.get('name'):
                        dict_e['name'] = ele.get('name')
                    if ele.get('id'):
                        dict_e['woo_id'] = ele.get('id')
                        url = "products/attributes/%s/terms" % ele.get('id')
                        data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc'})
                        if data.status_code == 200:
                            parsed_data = data.json()
                            if parsed_data:
                                for value in parsed_data:
                                    dict_value = {}
                                    existing_value = self.env['product.attribute.value'].search(
                                        ['|' ,('woo_id', '=', value.get('id')), ('name', '=', value.get('name'))], limit=1)
                                    if value.get('name'):
                                        dict_value['name'] = value.get('name')
                                    if value.get('id'):
                                        dict_value['woo_id'] = value.get('id')
                                    if value.get('slug'):
                                       dict_value['slug'] = value.get('slug')
                                    if value.get('description'):
                                        dict_value['description'] = value.get('description')
                                    if attribute.id and not existing_value:
                                        dict_value['attribute_id'] = attribute.id
                                        create_value = self.env['product.attribute.value'].create(dict_value)
                                    elif existing_value:
                                        if value.get('name'):
                                            existing_value.name = value.get('name')
                                        if value.get('slug'):
                                            existing_value.slug = value.get('slug')
                                        if value.get('description'):
                                            existing_value.description = value.get('description')

                    if ele.get('slug'):
                        dict_e['slug'] = ele.get('slug')

                    if not attribute and attribute_without_woo:
                        attribute_without_woo.write(dict_e)

                    if attribute and not attribute_without_woo:
                        attribute.write(dict_e)

                    if not attribute and not attribute_without_woo:
                        self.env['product.attribute'].create(dict_e)
        else:
            raise UserError(_("Something went wrong, Please Check the Connection"))


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    woo_id = fields.Char('WooCommerce Id')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)
    slug = fields.Char('Slug')
    description = fields.Text('Description')
    attribute_id = fields.Many2one('product.attribute', 'Attribute', required=1, copy=False)
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')

    def cron_import_product_attr_value(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute.value'].import_product_attribute_term(rec)

    def import_product_attribute_term(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )

        imported_attr = self.env['product.attribute'].search([])
        for rec in imported_attr:

            if rec.woo_id:
                url = "products/attributes/%s/terms" % rec.woo_id
                try:
                    data = wcapi.get(url)
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))
                if data.status_code == 200:
                    parsed_data = data.json()
                    if parsed_data:
                        for value in parsed_data:

                            existing_attr_value = self.env['product.attribute.value'].search(
                                ['|', ('woo_id', '=', value.get('id')), ('name', '=', value.get('name'))], limit=1)
                            dict_value = {}
                            if value.get('name'):
                                dict_value['name'] = value.get('name')
                            if rec.id:
                                dict_value['attribute_id'] = rec.id

                            if value.get('description'):
                                dict_value['description'] = value.get('description')
                            if value.get('id'):
                                dict_value['woo_id'] = value.get('id')
                            if value.get('slug'):
                                dict_value['slug'] = value.get('slug')
                            dict_value['woo_instance_id'] = instance_id.id
                            dict_value['is_exported'] = True

                            if not existing_attr_value and dict_value['attribute_id']:
                                self.env['product.attribute.value'].create(dict_value)

                            elif existing_attr_value:
                                existing_attr_value.write(dict_value)

    def cron_export_product_attr_value(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute.value'].export_selected_attribute_terms(rec)

    def export_selected_attribute_terms(self, instance_id):

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
        selected_records = self.env['product.attribute.value'].browse(selected_ids)
        all_records = self.env['product.attribute.value'].search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records
        list = []
        for rec in records:
            list.append({
                'id': rec.woo_id,
                'name': rec.name,
                'slug': rec.slug if rec.slug else '',
                'description': str(rec.description) if rec.description else ''
            })
        if list:
            for data in list:
                value = self.env['product.attribute.value'].search([('name', '=', data.get('name'))], limit=1)
                if data.get('id'):
                    try:
                        if value.attribute_id.woo_id:
                            wcapi.post("products/attributes/%s/terms/%s" % (value.attribute_id.woo_id, data.get('id')), data).json()
                        else:
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _("Sync your attribute"),
                                 'message': _(
                                     "The attribute %s  is not synced with WooCommerce") % value.attribute_id.name}
                            )
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))
                else:
                    try:
                        if value.attribute_id.woo_id:
                            wcapi.post("products/attributes/%s/terms" % value.attribute_id.woo_id, data).json()
                        else:
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _("Sync your attribute"),
                                 'message': _(
                                     "The attribute %s  is not synced with WooCommerce") % value.attribute_id.name}
                            )
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))
        self.import_product_attribute_term(instance_id)







