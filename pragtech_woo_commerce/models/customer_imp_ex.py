from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from woocommerce import API


class Customer(models.Model):
    _inherit = 'res.partner'

    woo_id = fields.Char('WooCommerce Id')
    commission_type = fields.Selection([
        ('global', 'Global'),
        ('percent', 'Percentage'),
        # ('fixed', 'Fixed')
    ], "Commission Type")
    commission_value = fields.Float("Commission for Admin")
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)

    def cron_export_customer(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['res.partner'].export_selected_customer(rec)

    def export_selected_customer(self, instance_id):

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
        selected_records = self.env['res.partner'].browse(selected_ids)
        all_records = self.env['res.partner'].search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records
        list = []
        for rec in records:
            dict_billing_address = {}
            dict_shipping_address = {}
            contacts_billing = self.env['res.partner'].search([('parent_id', '=', rec.id), ('type', '=', 'invoice')],
                                                              limit=1)
            contacts_shipping = self.env['res.partner'].search([('parent_id', '=', rec.id), ('type', '=', 'delivery')],
                                                               limit=1)

            if contacts_billing:
                dict_billing_address['email'] = str(rec.email)
                if contacts_billing.parent_id:
                    dict_billing_address['company'] = contacts_billing.parent_id.name
                if contacts_billing.street:
                    dict_billing_address['address_1'] = contacts_billing.street
                if contacts_billing.street2:
                    dict_billing_address['address_2'] = contacts_billing.street2
                if contacts_billing.city:
                    dict_billing_address['city'] = contacts_billing.city
                if contacts_billing.state_id:
                    dict_billing_address['state'] = contacts_billing.state_id.code
                if contacts_billing.zip:
                    dict_billing_address['postcode'] = contacts_billing.zip
                if contacts_billing.country_id:
                    dict_billing_address['country'] = contacts_billing.country_id.code
                if contacts_billing.phone:
                    dict_billing_address['phone'] = contacts_billing.phone
            else:
                dict_billing_address['email'] = rec.email
                if rec.parent_id:
                    dict_billing_address['company'] = rec.parent_id.name
                    dict_shipping_address['company'] = rec.parent_id.name
                if rec.street:
                    dict_billing_address['address_1'] = rec.street
                    dict_shipping_address['company'] = rec.parent_id.name
                if rec.street2:
                    dict_billing_address['address_2'] = rec.street2
                    dict_shipping_address['company'] = rec.parent_id.name
                if rec.city:
                    dict_billing_address['city'] = rec.city
                    dict_shipping_address['company'] = rec.parent_id.name
                if rec.state_id:
                    dict_billing_address['state'] = rec.state_id.code
                    dict_shipping_address['company'] = rec.parent_id.name
                if rec.zip:
                    dict_billing_address['postcode'] = rec.zip
                    dict_shipping_address['company'] = rec.parent_id.name
                if rec.country_id:
                    dict_billing_address['country'] = rec.country_id.code
                    dict_shipping_address['company'] = rec.parent_id.name
                if rec.phone:
                    dict_billing_address['phone'] = rec.phone
                    dict_shipping_address['company'] = rec.parent_id.name

            if contacts_shipping:
                dict_shipping_address['email'] = rec.email
                if contacts_shipping.parent_id:
                    dict_shipping_address['company'] = contacts_shipping.parent_id.name
                if contacts_shipping.street:
                    dict_shipping_address['address_1'] = contacts_shipping.street
                if contacts_shipping.street2:
                    dict_shipping_address['address_2'] = contacts_shipping.street2
                if contacts_shipping.city:
                    dict_shipping_address['city'] = contacts_shipping.city
                if contacts_shipping.state_id:
                    dict_shipping_address['state'] = contacts_shipping.state_id.code
                if contacts_shipping.zip:
                    dict_shipping_address['postcode'] = contacts_shipping.zip
                if contacts_shipping.country_id:
                    dict_shipping_address['country'] = contacts_shipping.country_id.code
                if contacts_shipping.phone:
                    dict_shipping_address['phone'] = contacts_shipping.phone
            else:
                dict_shipping_address['email'] = rec.email
                if rec.parent_id:
                    dict_shipping_address['company'] = rec.parent_id.name
                else:
                    dict_shipping_address['company'] = ''
                if rec.street:
                    dict_shipping_address['address_1'] = rec.street
                else:
                    dict_shipping_address['address_1'] = ''
                if rec.street2:
                    dict_shipping_address['address_2'] = rec.street2
                else:
                    dict_shipping_address['address_1'] = ''
                if rec.city:
                    dict_shipping_address['city'] = rec.city
                else:
                    dict_shipping_address['city'] = ''
                if rec.state_id:
                    dict_shipping_address['state'] = rec.state_id.code
                else:
                    dict_shipping_address['state'] = ''
                if rec.zip:
                    dict_shipping_address['postcode'] = rec.zip
                else:
                    dict_shipping_address['postcode'] = ''
                if rec.country_id:
                    dict_shipping_address['country'] = rec.country_id.code
                else:
                    dict_shipping_address['country'] = ''
                if rec.phone:
                    dict_shipping_address['phone'] = rec.phone
                else:
                    dict_shipping_address['phone'] = ''

            list.append({
                "id": rec.woo_id,
                "email": rec.email,
                "first_name": rec.name if rec.name else '',
                "username": rec.name if rec.name else '',
                "billing": dict_billing_address,
                "shipping": dict_shipping_address,
            })
        if list:
            for data in list:
                if data.get('id'):
                    try:
                        wcapi.post("customers/%s" % (data.get('id')), data).json()
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))

                else:
                    try:
                        parsed_data = wcapi.post("customers", data).json()
                        if parsed_data.get('code') == 'registration-error-email-exists':
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                                {'type': 'snailmail_invalid_address', 'title': _("Email already registered"),
                                 'message': _(
                                     "The email id for %s is already registered so the contact is not updated in WooCommerce") % data.get(
                                     'first_name')}
                            )
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))

        self.import_customer(instance_id)

    def cron_import_customer(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['res.partner'].import_customer(rec)

    def import_customer(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )

        url = "customers"
        try:
            data = wcapi.get(url)
        except Exception as error:
            raise UserError(_("Please check your connection and try again"))
        if data.status_code == 200:
            # self.woo_last_cust_total_page = int(data.headers['X-WP-TotalPages'])
            parsed_data = data.json()
            if parsed_data:
                for ele in parsed_data:
                    customer = self.env['res.partner'].search(
                        [('woo_id', '=', ele.get('id'))], limit=1)

                    ''' This is used to update woo_id of a customer, this
                    will avoid duplication of customer while syncing product category.
                    '''
                    customer_without_woo_id = self.env['res.partner'].search(
                        [('woo_id', '=', False), ('email', '=', ele.get('email')), ('type', '=', 'contact')], limit=1)

                    dict_p = {}

                    dict_p['woo_instance_id'] = instance_id.id
                    dict_p['company_id'] = instance_id.woo_company_id.id
                    dict_p['is_exported'] = True

                    if ele.get('id'):
                        dict_p['woo_id'] = ele.get('id')

                    if ele.get('first_name'):
                        dict_p['name'] = ele.get('first_name')
                    else:
                        dict_p['name'] = ''

                    if ele.get('email'):
                        dict_p['email'] = ele.get('email')
                    else:
                        dict_p['email'] = ''

                    if ele.get('billing'):

                        if ele.get('billing').get('phone'):
                            dict_p['phone'] = ele.get('billing').get('phone')
                        else:
                            dict_p['phone'] = ''

                    dict_p['customer_rank'] = 1

                    if not customer and customer_without_woo_id:
                        customer_without_woo_id.write(dict_p)

                    if not customer and not customer_without_woo_id:
                        '''If product_category is not present we create it'''

                        pro_create = customer.create(dict_p)
                        if pro_create:

                            if ele.get('billing'):
                                dict_a = {}
                                if ele.get('billing').get('phone'):
                                    dict_a['phone'] = ele.get('billing').get('phone')
                                else:
                                    dict_a['phone'] = ''
                                if ele.get('billing').get('email'):
                                    dict_a['email'] = ele.get('billing').get('email')
                                else:
                                    dict_a['email'] = ''

                                dict_a['parent_id'] = pro_create.id
                                dict_a['type'] = 'invoice'

                                if ele.get('billing').get('postcode'):
                                    dict_a['zip'] = ele.get('billing').get('postcode')
                                else:
                                    dict_a['zip'] = ''

                                if ele.get('billing').get('address_1'):
                                    dict_a['street'] = ele.get('billing').get('address_1')
                                else:
                                    dict_a['street'] = ''

                                if ele.get('billing').get('address_2'):
                                    dict_a['street2'] = ele.get('billing').get('address_2')
                                else:
                                    dict_a['street2'] = ''

                                if ele.get('billing').get('city'):
                                    dict_a['city'] = ele.get('billing').get('city')
                                else:
                                    dict_a['city'] = ''

                                if ele.get('billing').get('country'):
                                    country_id = self.env['res.country'].search(
                                        [('code', '=', ele.get('billing').get('country'))])

                                    dict_a['country_id'] = country_id.id

                                    if ele.get('billing').get('state'):

                                        state_id = self.env['res.country.state'].search(
                                            ['&', ('code', '=', ele.get('billing').get('state')),
                                             ('country_id', '=', country_id.id)])
                                        if state_id:
                                            dict_a['state_id'] = state_id.id
                                        else:
                                            dict_a['state_id'] = False
                                    child_create = customer.create(dict_a)

                            if ele.get('shipping'):
                                dict_s = {}
                                dict_s['parent_id'] = pro_create.id
                                dict_s['type'] = 'delivery'

                                if ele.get('shipping').get('postcode'):
                                    dict_s['zip'] = ele.get('shipping').get('postcode')
                                else:
                                    dict_s['zip'] = ''

                                if ele.get('shipping').get('address_1'):
                                    dict_s['street'] = ele.get('shipping').get('address_1')
                                else:
                                    dict_s['street'] = ''

                                if ele.get('shipping').get('address_2'):
                                    dict_s['street2'] = ele.get('shipping').get('address_2')
                                else:
                                    dict_s['street2'] = ''

                                if ele.get('shipping').get('city'):
                                    dict_s['city'] = ele.get('shipping').get('city')
                                else:
                                    dict_s['city'] = ''

                                if ele.get('shipping').get('country'):
                                    country_id = self.env['res.country'].search(
                                        [('code', '=', ele.get('shipping').get('country'))])

                                    dict_s['country_id'] = country_id.id

                                    if ele.get('shipping').get('state'):

                                        state_id = self.env['res.country.state'].search(
                                            ['&', ('code', '=', ele.get('shipping').get('state')),
                                             ('country_id', '=', country_id.id)])

                                        if state_id:

                                            dict_s['state_id'] = state_id.id
                                        else:
                                            dict_s['state_id'] = False

                                child_create = customer.create(dict_s)
                    else:
                        pro_create = customer.write(dict_p)
                        if pro_create:
                            '''Search for updated customer'''
                            customer_record = self.env['res.partner'].search(
                                [('woo_id', '=', ele.get('id'))])
                            if customer_record:
                                '''Search for billaddress id'''
                                customer_id = self.env['res.partner'].search(
                                    [('parent_id', '=', customer_record.id), ('type', '=', 'invoice')])
                                if customer_id:
                                    if ele.get('billing'):
                                        if ele.get('billing').get('phone'):
                                            phone = ele.get('billing').get('phone')
                                        else:
                                            phone = ''

                                        if ele.get('billing').get('postcode'):
                                            zip = ele.get('billing').get('postcode')
                                        else:
                                            zip = ''

                                        if ele.get('billing').get('address_1'):
                                            street = ele.get('billing').get('address_1')
                                        else:
                                            street = ''

                                        if ele.get('billing').get('address_2'):
                                            street2 = ele.get('billing').get('address_2')
                                        else:
                                            street2 = ''

                                        if ele.get('billing').get('city'):
                                            city = ele.get('billing').get('city')
                                        else:
                                            city = ''

                                        if ele.get('billing').get('country'):

                                            country_id = self.env['res.country'].search(
                                                [('code', '=', ele.get('billing').get('country'))])

                                            country = country_id.id

                                            if ele.get('billing').get('state'):
                                                state_id = self.env['res.country.state'].search(
                                                    ['&', ('code', '=', ele.get('billing').get('state')),
                                                     ('country_id', '=', country_id.id)])
                                                if state_id:
                                                    customer_id.write({'state_id': state_id.id})
                                                #     state = state_id.id
                                                # else:
                                                #     state = ''
                                            child_create = customer_id.write({
                                                'zip': zip,
                                                'city': city,
                                                'street': street,
                                                'street2': street2,
                                                'country_id': country,
                                                'phone': phone,
                                                'parent_id': customer_record.id,
                                                'type': 'invoice'
                                            })
                                else:

                                    '''CREATE NEW ADDRESS FOR EXISTING CUSTOMER'''
                                    if ele.get('billing'):
                                        dict_a = {}
                                        if ele.get('billing').get('phone'):
                                            dict_a['phone'] = ele.get('billing').get('phone')
                                        else:
                                            dict_a['phone'] = ''

                                        dict_a['parent_id'] = customer_record.id
                                        dict_a['type'] = 'invoice'

                                        if ele.get('billing').get('postcode'):
                                            dict_a['zip'] = ele.get('billing').get('postcode')
                                        else:
                                            dict_a['zip'] = ''

                                        if ele.get('billing').get('address_1'):
                                            dict_a['street'] = ele.get('billing').get('address_1')
                                        else:
                                            dict_a['street'] = ''

                                        if ele.get('billing').get('address_2'):
                                            dict_a['street2'] = ele.get('billing').get('address_2')
                                        else:
                                            dict_a['street2'] = ''

                                        if ele.get('billing').get('city'):
                                            dict_a['city'] = ele.get('billing').get('city')
                                        else:
                                            dict_a['city'] = ''

                                        if ele.get('billing').get('country'):
                                            country_id = self.env['res.country'].search(
                                                [('code', '=', ele.get('billing').get('country'))])

                                            dict_a['country_id'] = country_id.id

                                            if ele.get('billing').get('state'):

                                                state_id = self.env['res.country.state'].search(
                                                    ['&', ('code', '=', ele.get('billing').get('state')),
                                                     ('country_id', '=', country_id.id)])
                                                if state_id:
                                                    dict_a['state_id'] = state_id.id
                                                else:
                                                    dict_a['state_id'] = ''

                                            child_create = customer_record.create(dict_a)

                                '''//////--------------------   SHIPING ADDRESS ----------------------//////////'''

                                customer_id2 = self.env['res.partner'].search(
                                    [('parent_id', '=', customer_record.id), ('type', '=', 'delivery')])
                                if customer_id2:
                                    if ele.get('shipping'):
                                        dict_s = {}
                                        zip_s = ''
                                        city_s = ''
                                        street_s = ''
                                        street2_s = ''

                                        if ele.get('shipping').get('postcode'):
                                            zip_s = ele.get('shipping').get('postcode')

                                        if ele.get('shipping').get('address_1'):
                                            street_s = ele.get('shipping').get('address_1')

                                        if ele.get('shipping').get('address_2'):
                                            street2_s = ele.get('shipping').get('address_2')

                                        if ele.get('shipping').get('city'):
                                            city_s = ele.get('shipping').get('city')

                                        if ele.get('shipping').get('country'):
                                            country_id_s = self.env['res.country'].search(
                                                [('code', '=', ele.get('shipping').get('country'))])
                                            country_s = country_id_s.id

                                            if ele.get('shipping').get('state'):
                                                state_id_s = self.env['res.country.state'].search(
                                                    ['&', ('code', '=', ele.get('shipping').get('state')),
                                                     ('country_id', '=', country_id_s.id)])

                                                if state_id_s:
                                                    customer_id2.write({'state_id': state_id_s.id})
                                            child_create = customer_id2.write({
                                                'zip': zip_s,
                                                'city': city_s,
                                                'street': street_s,
                                                'street2': street2_s,
                                                'country_id': country_s,
                                                # 'phone': phone,
                                                'parent_id': customer_record.id,
                                                'type': 'delivery'
                                            })
                                else:

                                    if ele.get('shipping'):
                                        dict_ss = {}
                                        dict_ss['parent_id'] = customer_record.id
                                        dict_ss['type'] = 'delivery'

                                        if ele.get('shipping').get('postcode'):
                                            dict_ss['zip'] = ele.get('shipping').get('postcode')

                                        if ele.get('shipping').get('address_1'):
                                            dict_ss['street'] = ele.get('shipping').get('address_1')

                                        if ele.get('shipping').get('address_2'):
                                            dict_ss['street2'] = ele.get('shipping').get('address_2')

                                        if ele.get('shipping').get('city'):
                                            dict_ss['city'] = ele.get('shipping').get('city')

                                        if ele.get('shipping').get('country'):
                                            country_id_ss = self.env['res.country'].search(
                                                [('code', '=', ele.get('shipping').get('country'))])
                                            dict_ss['country_id'] = country_id_ss.id

                                            if ele.get('shipping').get('state'):
                                                state_id_ss = self.env['res.country.state'].search(
                                                    ['&', ('code', '=', ele.get('shipping').get('state')),
                                                     ('country_id', '=', country_id_ss.id)])

                                                if state_id_ss:
                                                    dict_ss['state_id'] = state_id_ss.id

                                        child_create = customer_record.create(dict_ss)

        else:
            raise UserError(_("Something went wrong, Please Check the Connection"))
