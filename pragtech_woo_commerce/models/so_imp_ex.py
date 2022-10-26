from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from woocommerce import API


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('order_line')
    def change_price_unit(self):
        if self.order_line:
            for line in self.order_line:
                if line.product_id.woo_id:
                    line.price_unit = line.product_id.woo_sale_price
                else:
                    line.price_unit = line.product_id.lst_price

    woo_id = fields.Char('WooCommerce Id')
    payment_type = fields.Selection([
        ('cod', 'COD'),
        ('prepaid', 'Prepaid')
    ], "Payment Type")
    is_exported = fields.Boolean('Synced In Woo', default=False)
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')

    def cron_export_sale_order(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['sale.order'].export_selected_so(rec)

    def export_selected_so(self, instance_id):
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
        selected_records = self.env['sale.order'].browse(selected_ids)
        all_records = self.env['sale.order'].search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records
        list = []
        for rec in records:
            order_lines = []
            for lines in rec.order_line:
                tax_lines = []
                for taxes in lines.tax_id:
                    tax_lines.append({
                        "id": taxes.woo_id if taxes.woo_id else 0,
                    })
                if lines.product_id.woo_id:
                    order_lines.append({
                        "product_id": lines.product_id.woo_id,
                        "quantity": lines.product_uom_qty,
                        "sku": lines.product_id.default_code if lines.product_id.default_code else '',
                        "price": str(lines.price_unit),
                        "total_tax": str(lines.price_tax),
                        "taxes": tax_lines,
                    })
            if rec.partner_id.woo_id:
                list.append({
                    "number": str(rec.name),
                    "id": rec.woo_id,
                    "customer_id": rec.partner_id.woo_id,
                    "currency": rec.currency_id.name,
                    "total_tax": rec.amount_tax,
                    "customer_note": rec.note,
                    "payment_method_title": str(rec.payment_term_id.name) if rec.payment_term_id else '',

                    "billing": {
                        "first_name": rec.partner_id.name if rec.partner_id.name else '',
                        "address_1": rec.partner_id.street if rec.partner_id.street else '',
                        "address_2": rec.partner_id.street2 if rec.partner_id.street2 else '',
                        "city": rec.partner_id.city if rec.partner_id.city else '',
                        "state": rec.partner_id.state_id.name if rec.partner_id.state_id else '',
                        "postcode": rec.partner_id.zip if rec.partner_id.zip else '',
                        "country": rec.partner_id.country_id.name if rec.partner_id.country_id else '',
                        "email": rec.partner_id.email if rec.partner_id.email else "example@gmail.com",
                        "phone": rec.partner_id.phone if rec.partner_id.phone else '',
                    },

                    "shipping": {
                        "first_name": rec.partner_id.name if rec.partner_id.name else '',
                        "address_1": rec.partner_id.street if rec.partner_id.street else '',
                        "address_2": rec.partner_id.street2 if rec.partner_id.street2 else '',
                        "city": rec.partner_id.city if rec.partner_id.city else '',
                        "state": rec.partner_id.state_id.name if rec.partner_id.state_id else '',
                        "postcode": rec.partner_id.zip if rec.partner_id.zip else '',
                        "country": rec.partner_id.country_id.name if rec.partner_id.country_id else '',
                    },
                    "line_items": order_lines,
                })
        if list:
            for data in list:
                if data.get('id'):
                    try:
                        wcapi.post("orders/%s" % (data.get('id')), data).json()
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))
                else:
                    try:
                        wcapi.post("orders", data).json()
                    except Exception as error:
                        raise UserError(_("Please check your connection and try again"))
        self.import_sale_order(instance_id)

    def cron_import_sale_order(self):
        all_instances = self.env['woo.instance'].search([])
        for rec in all_instances:
            if rec:
                self.env['sale.order'].import_sale_order(rec)

    def import_sale_order(self, instance_id):

        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )

        url = "orders"
        try:
            data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc'})
        except Exception as error:
            raise UserError(_("Please check your connection and try again"))

        if data.status_code == 200:
            parsed_data = data.json()
            if parsed_data:
                for ele in parsed_data:
                    dict_s = {}
                    # searching sales order
                    sale_order = self.env['sale.order'].search(
                        [('woo_id', '=', ele.get('id'))], limit=1)
                    dict_s['woo_instance_id'] = instance_id.id
                    dict_s['is_exported'] = True
                    dict_s['state'] = 'sale'
                    dict_s['company_id'] = instance_id.woo_company_id.id
                    if not sale_order:
                        dict_s['woo_id'] = ele.get('id')
                        res_partner = self.env['res.partner'].search(
                            [('woo_id', '=', ele.get('customer_id'))], limit=1)
                        if res_partner:
                            if ele.get('id'):
                                dict_s['partner_id'] = res_partner.id
                                dict_s['state'] = 'sale'
                                dict_s['woo_id'] = ele.get('id')

                            if ele.get('number'):
                                dict_s['name'] = '#' + str(ele.get('number'))

                            if ele.get('payment_details'):
                                if ele.get('payment_details').get('method_title'):
                                    pay_id = self.env['account.payment.term']
                                    payment = pay_id.search(
                                        [('name', '=', ele.get('payment_details').get('method_title'))], limit=1)
                                    if not payment:
                                        create_payment = payment.create({
                                            'name': ele.get('payment_details').get('method_title')
                                        })
                                        if create_payment:
                                            dict_s['payment_term_id'] = create_payment.id
                                    else:
                                        dict_s['payment_term_id'] = payment.id

                            if ele.get('total'):
                                dict_s['amount_total'] = float(ele.get('total'))

                            so_obj = self.env['sale.order'].create(dict_s)
                            for i in ele.get('line_items'):
                                res_product = self.env['product.product'].search(
                                    ['|', ('woo_id', '=', i.get('product_id')), ('woo_id','=', i.get('variation_id'))], limit=1)
                                if res_product:
                                    dict_l = {}
                                    if i.get('id'):
                                        dict_l['w_id'] = i.get('id')
                                    dict_l['order_id'] = so_obj.id
                                    dict_l['product_id'] = res_product.id

                                    if i.get('quantity'):
                                        dict_l['product_uom_qty'] = i.get('quantity')

                                    if i.get('taxes'):
                                        for t in i.get('taxes'):
                                            existing_tax = self.env['account.tax'].search(
                                                [('woo_id', '=', t.get('id'))])
                                            if existing_tax:
                                                dict_l['tax_id'] = [(6, 0, [existing_tax.id])]

                                    if i.get('currency'):
                                        cur_id = self.env['res.currency'].search(['name', '=', 'currency'], limit=1)
                                        dict_l['currency_id'] = cur_id.id

                                    if i.get('price'):
                                        dict_l['price_unit'] = float(i.get('price'))

                                    if i.get('subtotal'):
                                        dict_l['price_subtotal'] = float(i.get('subtotal'))

                                    if 'meta_data' in i and i.get('meta_data'):
                                        for record in i.get('meta_data'):
                                            if 'key' in record and record.get('key') == '_vendor_id':
                                                vendor_id = self.env['res.partner'].search(
                                                    [('woo_id', '=', record.get('value'))], limit=1)
                                                dict_l['woo_vendor'] = vendor_id.id

                                    create_p = self.env['sale.order.line'].create(dict_l)

                            if ele.get('payment_method') == 'cod':
                                so_obj.payment_type = 'cod'
                            else:
                                so_obj.payment_type = 'prepaid'

                            if ele.get('date_paid'):
                                so_obj.action_confirm()
                                so_obj._prepare_invoice()
                                so_obj._create_invoices()

                    else:
                        res_partner = self.env['res.partner'].search(
                            [('woo_id', '=', ele.get('customer_id'))], limit=1)
                        if res_partner:
                            dict_s = {}

                            if ele.get('id'):
                                dict_s['partner_id'] = res_partner.id
                                dict_s['woo_id'] = ele.get('id')
                                dict_s['state'] = 'draft'

                            if ele.get('number'):
                                dict_s['name'] = ele.get('number')

                            if ele.get('payment_details'):
                                if ele.get('payment_details').get('method_title'):
                                    pay_id = self.env['account.payment.term']
                                    payment = pay_id.search(
                                        [('name', '=', ele.get('payment_details').get('method_title'))], limit=1)
                                    if not payment:
                                        create_payment = payment.create({

                                            'name': ele.get('payment_details').get('method_title')
                                        })
                                        if create_payment:
                                            dict_s['payment_term_id'] = create_payment.id
                                    else:
                                        dict_s['payment_term_id'] = payment.id

                            if ele.get('total'):
                                dict_s['amount_total'] = ele.get('total')

                            update_so = self.env['sale.order'].write(dict_s)
                            for i in ele.get('line_items'):

                                res_product = self.env['product.product'].search(
                                    ['|', ('woo_id', '=', i.get('product_id')),  ('woo_id','=', i.get('variation_id'))], limit=1)

                                if res_product:
                                    s_order_line = self.env['sale.order.line'].search(
                                        [('product_id', '=', res_product.id),
                                         (('order_id', '=', sale_order.id))], limit=1)

                                    if s_order_line:
                                        dict_lp = {}
                                        quantity = 0
                                        ol_qb_id = 0
                                        sp = 0
                                        product_tax_id = 0
                                        if i.get('quantity'):
                                            quantity = i.get('quantity')

                                        if i.get('id'):
                                            ol_qb_id = i.get('id')

                                        if i.get('price'):
                                            sp = i.get('price')

                                        if i.get('total_tax'):
                                            tax = self.env['account.tax']

                                            if float(i.get('subtotal')):
                                                total_tax = (float(float(i.get('total_tax')) / float(
                                                    i.get('subtotal'))) * 100)
                                            else:
                                                total_tax = 0

                                            tax_name = "WTax " + '' + str(total_tax) + '%'
                                            record = tax.search(
                                                [('amount', '=', total_tax), ('name', '=', tax_name),
                                                 ('type_tax_use', '=', 'sale')], limit=1)

                                            _tax_group_id = self.env['account.tax.group'].search(
                                                [('name', '=', tax_name)], limit=1)
                                            if _tax_group_id:

                                                if not record:
                                                    create_tax = record.create({

                                                        'amount': total_tax,
                                                        'name': "WTax " + '' + str(total_tax) + '%',
                                                        'amount_type': 'percent',
                                                        'company_id': instance_id.woo_company_id.id,
                                                        'sequence': 1,
                                                        'type_tax_use': 'sale',
                                                        'tax_group_id': _tax_group_id.id,
                                                    })
                                                    if create_tax:
                                                        product_tax_id = [(6, 0, [create_tax.id])]
                                                else:
                                                    update_tax = record.write({
                                                        'amount': total_tax,
                                                    })
                                                    if update_tax:
                                                        product_tax_id = [(6, 0, [record.id])]
                                            else:

                                                tax_group = _tax_group_id.create({
                                                    'name': tax_name
                                                })

                                                if not record:
                                                    create_tax = record.create({

                                                        'amount': total_tax,
                                                        'name': "WTax " + '' + str(total_tax) + '%',
                                                        'amount_type': 'percent',
                                                        'company_id': instance_id.woo_company_id.id,
                                                        'sequence': 1,
                                                        'type_tax_use': 'sale',
                                                        'tax_group_id': tax_group.id,
                                                    })
                                                    if create_tax:
                                                        product_tax_id = [(6, 0, [create_tax.id])]
                                                else:

                                                    update_tax = record.write({
                                                        'amount': total_tax,
                                                    })

                                                    if update_tax:
                                                        product_tax_id = [(6, 0, [record.id])]

                                        vendor_id = None
                                        if 'meta_data' in i and i.get('meta_data'):
                                            for record in i.get('meta_data'):
                                                if 'key' in record and record.get('key') == '_vendor_id':
                                                    vendor_id = self.env['res.partner'].search(
                                                        [('woo_id', '=', record.get('value'))], limit=1)

                                        create_po = self.env['sale.order.line'].search(
                                            ['&', ('product_id', '=', res_product.id),
                                             (('order_id', '=', sale_order.id))], limit=1)

                                        if create_po:
                                            res = create_po.update({

                                                'product_id': res_product.id,
                                                # 'name': description,
                                                'product_uom_qty': quantity,
                                                'w_id': ol_qb_id,
                                                # 'product_uom': 1,
                                                'price_unit': sp,
                                                'tax_id': product_tax_id,
                                                # 'woo_vendor': vendor_id.id
                                            })
                                    else:
                                        res_product = self.env['product.product'].search(
                                            ['|', ('woo_id', '=', i.get('product_id')),  ('woo_id','=', i.get('variation_id'))], limit=1)

                                        if res_product:

                                            dict_l = {}
                                            if i.get('id'):
                                                dict_l['w_id'] = i.get('id')

                                            dict_l['order_id'] = sale_order.id

                                            dict_l['product_id'] = res_product.id

                                            if i.get('quantity'):
                                                dict_l['product_uom_qty'] = i.get('quantity')

                                            if i.get('price'):
                                                dict_l['price_unit'] = i.get('price')

                                            if i.get('total_tax'):
                                                total_tax = (float(float(i.get('total_tax')) / float(
                                                    i.get('subtotal'))) * 100)

                                                tax_name = "WTax " + '' + str(total_tax) + '%'

                                                tax = self.env['account.tax']
                                                record = tax.search(
                                                    [('amount', '=', total_tax), ('name', '=', tax_name),
                                                     ('type_tax_use', '=', 'sale')], limit=1)
                                                _tax_group_id = self.env['account.tax.group'].search(
                                                    [('name', '=', tax_name)], limit=1)
                                                if _tax_group_id:

                                                    if not record:
                                                        create_tax = record.create({

                                                            'amount': total_tax,
                                                            'name': "WTax " + '' + str(total_tax) + "%",
                                                            'amount_type': 'percent',
                                                            'company_id': instance_id.woo_company_id.id,
                                                            'sequence': 1,
                                                            'type_tax_use': 'sale',
                                                            'tax_group_id': _tax_group_id.id,
                                                        })
                                                        if create_tax:
                                                            dict_l['tax_id'] = [(6, 0, [create_tax.id])]
                                                    else:

                                                        dict_l['tax_id'] = [(6, 0, [record.id])]
                                                else:
                                                    tax_group = _tax_group_id.create({
                                                        'name': tax_name
                                                    })
                                                    if not record:

                                                        create_tax = record.create({
                                                            'amount': total_tax,
                                                            'name': "WTax " + '' + str(total_tax) + "%",
                                                            'amount_type': 'percent',
                                                            'company_id': instance_id.woo_company_id.id,
                                                            'sequence': 1,
                                                            'type_tax_use': 'sale',
                                                            'tax_group_id': tax_group.id,
                                                        })
                                                        if create_tax:
                                                            dict_l['tax_id'] = [(6, 0, [create_tax.id])]
                                                    else:

                                                        dict_l['tax_id'] = [(6, 0, [record.id])]

                                            if i.get('currency'):
                                                cur_id = self.env['res.currency'].search(
                                                    ['name', '=', 'currency'], limit=1)
                                                dict_l['currency_id'] = cur_id.id

                                            vendor_id = None
                                            if 'meta_data' in i and i.get('meta_data'):
                                                for record in i.get('meta_data'):
                                                    if 'key' in record and record.get('key') == '_vendor_id':
                                                        vendor_id = self.env['res.partner'].search(
                                                            [('woo_id', '=', record.get('value'))], limit=1)
                                                        dict_l['woo_vendor'] = vendor_id.id

                                            create_p = self.env['sale.order.line'].create(dict_l)

        else:
            raise UserError(_("Something went wrong, Please Check the Connections"))


class SalerOrderLine(models.Model):
    _inherit = 'sale.order.line'

    w_id = fields.Char('WooCommerce Id')
    woo_vendor = fields.Many2one('res.partner', 'Woo Commerce Vendor')
