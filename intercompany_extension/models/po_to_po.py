# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime, date, time

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import is_html_empty


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    @api.model
    def default_get(self, fields_list):
        default_vals = super(PurchaseOrder, self).default_get(fields_list)
        if "purchase_order_template_id" in fields_list and not default_vals.get("purchase_order_template_id"):
            company_id = default_vals.get('company_id', False)
            company = self.env["res.company"].browse(company_id) if company_id else self.env.company
            default_vals['purchase_order_template_id'] = company.purchase_order_template_id.id
        return default_vals




    purchase_order_template_id = fields.Many2one(
        'purchase.order.template', 'Quotation Template',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="[('company_id', '=', False), ('company_ids', 'in', company_id)]")
    purchase_order_option_ids = fields.One2many(
        'purchase.order.option', 'order_id', 'Optional Products Lines',
        copy=True, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

    tag_ids = fields.Many2many('template.tag', string="Tag" , compute="compute_po_tags")
    for_ids = fields.Many2many('res.company', string='For ID', check_company=False, compute="compute_po_tags")
    for_ids_name = fields.Char(string="For : ", related='for_ids.name')
    tag_ids_name = fields.Char(string="For : ", related='tag_ids.name')
    auto_sale_order_id = fields.Many2one('sale.order', string='Source Sales Order', readonly=True, copy=False)
    source_po_id = fields.Many2one('purchase.order', string='Source PO Order', readonly=True, copy=False)
    auto_generated = fields.Boolean(string='Auto Generated Purchase Order', copy=False)
    second_auto_generated = fields.Boolean(string='Auto Generated Purchase Order', copy=False, default=False)
    price_list_id = fields.Many2one('product.supplierinfo', string="Vendor Pricelist")
    date_planned = fields.Datetime(compute='compute_date_panned')
    user_is_cost_viewer = fields.Boolean(string="Cost Viewer", compute='compute_value')

    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, change_default=True, tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="You can find a vendor by its Name, TIN, Email or Internal Reference.")



    def compute_value(self):
        for rec in self:
            if self.env.user.cost_viewer == True:
                rec.user_is_cost_viewer = True
            else:
                rec.user_is_cost_viewer = False




    @api.onchange('purchase_order_template_id')
    def compute_date_panned(self):
        for rec in self:
            rec.date_planned = datetime.now()

    @api.onchange('date_planned')
    def default_vendor(self):
        for rec in self:
            if self.env.company.id != 1:
                rec.partner_id = 1
            else:
                continue




####################################### PO to SO Functions ############################




    def button_approve(self, force=False):
        """ Generate inter company sales order base on conditions."""
        res = super(PurchaseOrder, self).button_approve(force=force)
        for order in self:
            # get the company from partner then trigger action of intercompany relation
            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.rule_type in ('purchase', 'sale_purchase') and (not order.auto_generated):
                order.with_user(company_rec.intercompany_user_id).with_context(default_company_id=company_rec.id).with_company(company_rec).inter_company_create_sale_order(company_rec)
        return res




###################################################
#                                                 #
# INTERCOMPANY LOGIC CREATE SO FROM CURRENT PO    #
###################################################




    def inter_company_create_sale_order(self, company):
        """ Create a Sales Order from the current PO (self)
            Note : In this method, reading the current PO is done as sudo, and the creation of the derived
            SO as intercompany_user, minimizing the access right required for the trigger user.
            :param company : the company of the created PO
            :rtype company : res.company record
        """
        # find user for creating and validation SO/PO from partner company
        intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not intercompany_uid:
            raise UserError(_(
                'Provide at least one user for inter company relation for %(name)s',
                name=company.name,
            ))
        # check intercompany user access rights
        if not self.env['sale.order'].check_access_rights('create', raise_exception=False):
            raise UserError(_(
                "Inter company user of company %(name)s doesn't have enough access rights",
                name=company.name,
            ))

        for rec in self:
            # check pricelist currency should be same with SO/PO document
            company_partner = rec.company_id.partner_id.with_user(intercompany_uid)
            if rec.currency_id.id != company_partner.property_product_pricelist.currency_id.id:
                raise UserError(_(
                    'You cannot create SO from PO because sale price list currency is different '
                    'than purchase price list currency.\n'
                    'The currency of the SO is obtained from the pricelist of the company partner.\n\n'
                    '(SO currency: %(so_currency)s, Pricelist: %(pricelist)s, Partner: %(partner)s (ID: %(id)s))',
                    so_currency=rec.currency_id.name,
                    pricelist=company_partner.property_product_pricelist.display_name,
                    partner=company_partner.display_name,
                    id=company_partner.id,
                ))

            # create the SO and generate its lines from the PO lines
            # read it as sudo, because inter-compagny user can not have the access right on PO


            direct_delivery_address = rec.picking_type_id.warehouse_id.partner_id.id or rec.dest_address_id.id
            sale_order_data = rec.sudo()._prepare_sale_order_data(
                rec.name, company_partner, company,
                direct_delivery_address or False)
            inter_user = self.env['res.users'].sudo().browse(intercompany_uid)
            # lines are browse as sudo to access all data required to be copied on SO line (mainly for company dependent field like taxes)
            for line in rec.order_line.sudo():
                sale_order_data['order_line'] += [(0, 0, rec._prepare_sale_order_line_data(line, company))]
            sale_order = self.env['sale.order'].with_context(allowed_company_ids=inter_user.company_ids.ids).with_user(intercompany_uid).create(sale_order_data)
            sale_order.order_line._compute_tax_id()
            msg = _("Automatically generated from %(origin)s of company %(company)s.", origin=self.name, company=rec.company_id.name)
            sale_order.message_post(body=msg)

            # write vendor reference field on PO
            if not rec.partner_ref:
                rec.partner_ref = sale_order.name

            #Validation of sales order
            if company.auto_validation:
                sale_order.with_user(intercompany_uid).action_confirm()


    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        """ Generate the Sales Order values from the PO
            :param name : the origin client reference
            :rtype name : string
            :param partner : the partner reprenseting the company
            :rtype partner : res.partner record
            :param company : the company of the created SO
            :rtype company : res.company record
            :param direct_delivery_address : the address of the SO
            :rtype direct_delivery_address : res.partner record
        """
        self.ensure_one()
        partner_addr = partner.sudo().address_get(['invoice', 'delivery', 'contact'])
        warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False


        if not warehouse:
            raise UserError(_('Configure correct warehouse for company(%s) from Menu: Settings/Users/Companies', company.name))

        # internal_pick = self.env['stock.picking.type'].search(
        #     [('code', '=', 'internal'), ('company_id', '=', company.id)])
        # if internal_pick and not self.purchase_order_template_id.target_partner_id:
        #     direct_delivery_address = internal_pick.warehouse_id.partner_id.id
        #     warehouse = internal_pick.warehouse_id
        #     print(internal_pick)
        #     print(direct_delivery_address)
        #     print(warehouse)
        # else:
        #     direct_delivery_address = direct_delivery_address
        #     warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False

        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('sale.order') or '/',
            'company_id': company.id,
            'team_id': self.env['crm.team'].with_context(allowed_company_ids=company.ids)._get_default_team_id(
                domain=[('company_id', '=', company.id)]).id,
            'warehouse_id': warehouse.id,
            'client_order_ref': name,
            'partner_id': partner.id,
            'partner_invoice_id': partner_addr['invoice'],
            'date_order': self.date_order,
            'fiscal_position_id': partner.property_account_position_id.id,
            'payment_term_id': partner.property_payment_term_id.id,
            'tag_ids': self.tag_ids,
            'for_ids': self.for_ids,
            'user_id': False,
            'auto_generated': True,
            'second_auto_generated': self.second_auto_generated,
            'auto_purchase_order_id': self.id,
            'auto_po_name': self.name,
            'partner_shipping_id': direct_delivery_address or partner_addr['delivery'],
            'order_line': [],
        }




    @api.model
    def _prepare_sale_order_line_data(self, line, company):
        """ Generate the Sales Order Line values from the PO line
            :param line : the origin Purchase Order Line
            :rtype line : purchase.order.line record
            :param company : the company of the created SO
            :rtype company : res.company record
        """
        # it may not affected because of parallel company relation
        price = line.price_unit or 0.0
        quantity = line.product_id and line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id) or line.product_qty
        price = line.product_id and line.product_uom._compute_price(price, line.product_id.uom_id) or price

        # if line.order_id.second_auto_generated:

        return {
            'name': line.name,
            'product_uom_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_id.id or line.product_uom.id,
            'price_unit': line.vendor_price,
            'vendor_price': line.vendor_price,
            'po_comment': line.po_comment,
            'customer_lead': line.product_id and line.product_id.sale_delay or 0.0,
            'company_id': company.id,
            'display_type': line.display_type,
        }



############################ PO to PO Functions #########################

    @api.onchange('purchase_order_template_id')
    def compute_po_tags(self):
        for rec in self:
            if rec.second_auto_generated == True:
                rec.for_ids = rec.source_po_id.company_id
                rec.tag_ids = rec.source_po_id.purchase_order_template_id.tag_ids

            elif rec.second_auto_generated == False:
                rec.tag_ids = rec.purchase_order_template_id.tag_ids
                rec.for_ids = rec.company_id





    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if self.purchase_order_template_id and self.purchase_order_template_id.number_of_days > 0:
            default = dict(default or {})
            default['validity_date'] = fields.Date.context_today(self) + timedelta(self.purchase_order_template_id.number_of_days)
        return super(PurchaseOrder, self).copy(default=default)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(PurchaseOrder, self).onchange_partner_id()
        template = self.purchase_order_template_id.with_context(lang=self.partner_id.lang)
        # self.note = template.note if not is_html_empty(template.note) else self.note

    def _compute_line_data_for_template_change(self, line):
        return {
            'display_type': line.display_type,
            'name': line.name,
            'state': 'draft',
        }

    def _compute_option_data_for_template_change(self, option):
        price = option.price_unit
        discount = 0

        return {
            'product_id': option.product_id.id,
            'name': option.name,
            'quantity': option.quantity,
            'uom_id': option.uom_id.id,
            'price_unit': price,
            # 'discount': discount
        }



    @api.onchange('purchase_order_template_id')
    def onchange_purchase_order_template_id(self):

        template = self.purchase_order_template_id.with_context(lang=self.partner_id.lang)

        # --- first, process the list of products from the template
        order_lines = [(5, 0, 0)]
        for line in template.purchase_order_template_line_ids:
            data = self._compute_line_data_for_template_change(line)

            if line.product_id:
                price = line.price_unit
                data.update({
                    'price_unit': price,
                    'product_qty': line.product_uom_qty,
                    'product_uom_qty': line.product_uom_qty,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                })

            order_lines.append((0, 0, data))

        self.order_line = order_lines
        self.order_line._compute_tax_id()

        # then, process the list of optional products from the template
        option_lines = [(5, 0, 0)]
        for option in template.purchase_order_template_option_ids:
            data = self._compute_option_data_for_template_change(option)
            option_lines.append((0, 0, data))

        self.purchase_order_option_ids = option_lines

        if template.number_of_days > 0:
            self.validity_date = fields.Date.context_today(self) + timedelta(template.number_of_days)


    def action_confirm(self):
        res = super(PurchaseOrder, self).action_confirm()
        if self.env.su:
            self = self.with_user(SUPERUSER_ID)

        for order in self:
            if order.purchase_order_template_id and order.purchase_order_template_id.mail_template_id:
                self.purchase_order_template_id.mail_template_id.send_mail(order.id)
        return res

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online quote if it exists. """
        self.ensure_one()
        user = access_uid and self.env['res.users'].sudo().browse(access_uid) or self.env.user

        if not self.purchase_order_template_id or (not user.share and not self.env.context.get('force_website')):
            return super(PurchaseOrder, self).get_access_action(access_uid)
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'self',
            'res_id': self.id,
        }




#################################################
#                                               #
# INTER COMPANY LOGIC CREATE PO From CURRENT PO #
#                                               #
#################################################



    def button_approve(self, force=False):
        """ Generate inter company purchase order based on conditions """
        res = super(PurchaseOrder, self).button_approve(force=force)
        for order in self:
            if not order.company_id or not order.purchase_order_template_id.target_partner_id: # if company_id not found, return to normal behavior
                continue
            # if company allow to create a Purchase Order from Sales Order, then do it !
            target_company = self.env['res.company']._find_company_from_partner(order.purchase_order_template_id.target_partner_id.id)
            company = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company or order.purchase_order_template_id.target_partner_id and company.rule_type in ('purchase', 'sale_purchase') and (not order.auto_generated):
                order.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(company).inter_company_create_purchase_order(company)
        return res




    def inter_company_create_purchase_order(self, company):
        """ Create a Purchase Order from the current PO (self)
            Note : In this method, reading the current PO is done as sudo, and the creation of the derived
            PO as intercompany_user, minimizing the access right required for the trigger user
            :param company : the company of the created PO
            :rtype company : res.company record
        """
        for rec in self:
            if not company:
                continue

            # find user for creating and validating SO/PO from company
            intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
            if not intercompany_uid:
                raise UserError(_('Provide one user for intercompany relation for % ') % company.name)
            # check intercompany user access rights
            if not self.env['purchase.order'].with_user(intercompany_uid).check_access_rights('create', raise_exception=False):
                raise UserError(_("Inter company user of company %s doesn't have enough access rights", company.name))

            company_partner = rec.partner_id.with_user(intercompany_uid)

            # company_partner = rec.purchase_order_template_id.target_company_id.partner_id
            # create the PO and generate its lines from the SO
            # read it as sudo, because inter-compagny user can not have the access right on PO
            po_vals = rec.sudo()._prepare_purchase_order_data(company, company_partner)
            inter_user = self.env['res.users'].sudo().browse(intercompany_uid)
            for line in rec.order_line.sudo():
                po_vals['order_line'] += [(0, 0, rec._prepare_purchase_order_line_data(line, rec.date_order, company))]
            purchase_order = self.env['purchase.order'].create(po_vals)
            purchase_order.order_line._compute_tax_id()
            msg = _("Automatically generated from %(origin)s of company %(company)s.", origin=self.name, company=company.name)
            purchase_order.message_post(body=msg)



            # auto-validate the purchase order if needed
            if company.auto_validation:
                purchase_order.with_user(intercompany_uid).button_confirm()





    def _prepare_purchase_order_data(self, company, company_partner):
        """ Generate purchase order values, from the SO (self)
            :param company_partner : the partner representing the company of the PO
            :rtype company_partner : res.partner record
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        self.ensure_one()
        # find location and warehouse, pick warehouse from company object
        # warehouse = self.purchase_order_template_id.target_company_id.warehouse_id or False# and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False
        # warehouse = self.env['stock.warehouse'].search([('company_id','=',self.purchase_order_template_id.target_company_id.partner_id.id)])
        # warehouse = company_partner.company_id.warehouse_id #and company_partner.company_id.warehouse_id.company_id.id == company.id and company_partner.company_id.warehouse_id or False
        # warehouse = self.partner_id.property_stock_supplier
        warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False

        if not warehouse:
            raise UserError(_('Configure correct warehouse for company(%s) from Menu: Settings/Users/Companies', company.name))
        picking_type_id = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'incoming'), ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        if not picking_type_id:
            intercompany_uid = company.intercompany_user_id.id
            picking_type_id = self.env['purchase.order'].with_user(intercompany_uid).default_picking_type()

        if company:
            return {
                'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
                'origin': self.name,
                'partner_id': self.purchase_order_template_id.target_partner_id.id,
                'date_order': self.date_order,
                'company_id': company.id,
                'fiscal_position_id': company_partner.property_account_position_id.id,
                'payment_term_id': company_partner.property_supplier_payment_term_id.id,
                'tag_ids': self.tag_ids,
                'for_ids': self.for_ids,
                'for_ids_name': self.for_ids_name,
                'tag_ids_name': self.tag_ids_name,
                'auto_generated': False,
                'second_auto_generated': True,
                'source_po_id': self.id,
                'partner_ref': self.name,
                'currency_id': self.currency_id.id,
                'order_line': [],
            }

        elif self.purchase_order_template_id.target_partner_id:
            return {
                'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
                'origin': self.name,
                'partner_id': self.purchase_order_template_id.target_partner_id.id,
                'date_order': self.date_order,
                'company_id': company.id,
                'fiscal_position_id': company_partner.property_account_position_id.id,
                'payment_term_id': company_partner.property_supplier_payment_term_id.id,
                'tag_ids': self.tag_ids,
                'for_ids': self.for_ids,
                'for_ids_name': self.for_ids_name,
                'tag_ids_name': self.tag_ids_name,
                'auto_generated': True,
                'second_auto_generated': True,
                'source_po_id': self.id,
                'partner_ref': self.name,
                'currency_id': self.currency_id.id,
                'order_line': [],
            }



    @api.model
    def _prepare_purchase_order_line_data(self, line, date_order, company):
        """ Generate purchase order line values, from the SO line
            :param so_line : origin SO line
            :rtype so_line : sale.order.line record
            :param date_order : the date of the orgin SO
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        # price on PO so_line should be so_line - discount
        price = line.price_unit# - (line.price_unit * (line.discount / 100))
        quantity = line.product_id and line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_po_id) or line.product_qty

        price = line.product_id and line.product_uom._compute_price(price, line.product_id.uom_po_id) or price
        vendor_price = line.vendor_price

        return {
                'name': line.name,
                'product_qty': quantity,
                'product_id': line.product_id and line.product_id.id or False,
                'product_uom': line.product_id and line.product_id.uom_po_id.id or line.product_uom.id,
                'price_unit': vendor_price,# if line.order_id.purchase_order_template_id else price,
                'company_id': company.id,
                'display_type': line.display_type,
                'po_comment': line.po_comment,
        }



class PurchaseOrderLine(models.Model):

    _inherit = "purchase.order.line"
    _description = "Purchase Order Line"


    purchase_order_option_ids = fields.One2many('purchase.order.option', 'line_id', 'Optional Products Lines')
    vendor_price = fields.Monetary(string='Price', compute='compute_price')
    user_is_cost_viewer = fields.Boolean(string="Cost Viewer", compute='compute_value')
    price_unit = fields.Float(string='Unit Price', digits='Product Price', readonly=False)
    po_comment = fields.Char(string="PO Comment", default="")

    @api.onchange('product_id')
    def compute_price(self):
        template_search = self.env['purchase.order.template']
        for rec in self:
            if rec.order_id.second_auto_generated == True:
                for vendors in rec.product_id.seller_ids:
                    if vendors.name == rec.order_id.partner_id and vendors.company_id == rec.order_id.company_id:
                        rec.vendor_price = vendors.price
                        rec.price_unit = rec.vendor_price or 0.0
                    else:
                        rec.vendor_price = rec.price_unit or 0.0
                else:
                    rec.vendor_price = rec.price_unit or 0.0
            elif rec.order_id.purchase_order_template_id and rec.order_id.second_auto_generated == False:
                for line in rec.order_id.purchase_order_template_id.purchase_order_template_line_ids:
                    if rec.product_id in line.product_id:
                        rec.price_unit = line.price_unit

                rec.vendor_price = rec.price_unit or 0.0
            else:
                rec.vendor_price = rec.price_unit or 0.0


    @api.onchange('product_qty')
    def recompute_subtotal(self):
        for rec in self:
            if rec.order_id.purchase_order_template_id :
                rec.price_unit = rec.vendor_price



    def compute_value(self):
        for rec in self:
            if self.env.user.cost_viewer == True:
                rec.user_is_cost_viewer = True
            else:
                rec.user_is_cost_viewer = False



class PurchaseOrderOption(models.Model):
    _name = "purchase.order.option"
    _description = "Purchase Options"
    _order = 'sequence, id'

    is_present = fields.Boolean(string="Present on Quotation",
                           help="This field will be checked if the option line's product is "
                                "already present in the quotation.",
                           compute="_compute_is_present", search="_search_is_present")
    order_id = fields.Many2one('purchase.order', 'Purchase Order Reference', ondelete='cascade', index=True)
    line_id = fields.Many2one('purchase.order.line', ondelete="set null", copy=False)
    name = fields.Text('Description', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('purchase_ok', '=', True)])
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    discount = fields.Float('Discount (%)', digits='Discount')
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure ', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    quantity = fields.Float('Quantity', required=True, digits='Product Unit of Measure', default=1)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of optional products.")

    @api.depends('line_id', 'order_id.order_line', 'product_id')
    def _compute_is_present(self):
        # NOTE: this field cannot be stored as the line_id is usually removed
        # through cascade deletion, which means the compute would be false
        for option in self:
            option.is_present = bool(option.order_id.order_line.filtered(lambda l: l.product_id == option.product_id))

    def _search_is_present(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('line_id', '=', False)]
        return [('line_id', '!=', False)]

    @api.onchange('product_id', 'uom_id', 'quantity')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.quantity,
            date=self.order_id.date_order,
            # pricelist=self.order_id.pricelist_id.id,
            uom=self.uom_id.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )
        self.name = product.get_product_multiline_description_sale()
        self.uom_id = self.uom_id or product.uom_id
        # To compute the discount a so line is created in cache
        values = self._get_values_to_add_to_order()
        new_sol = self.env['purchase.order.line'].new(values)
        new_sol._onchange_discount()
        self.discount = new_sol.discount


    def button_add_to_order(self):
        self.add_option_to_order()

    def add_option_to_order(self):
        self.ensure_one()

        purchase_order = self.order_id

        if purchase_order.state not in ['draft', 'sent']:
            raise UserError(_('You cannot add options to a confirmed order.'))

        values = self._get_values_to_add_to_order()
        order_line = self.env['purchase.order.line'].create(values)
        order_line._compute_tax_id()

        self.write({'line_id': order_line.id})
        if purchase_order:
            purchase_order.add_option_to_order_with_taxcloud()


    def _get_values_to_add_to_order(self):
        self.ensure_one()
        return {
            'order_id': self.order_id.id,
            'price_unit': self.price_unit,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'discount': self.discount,
            'company_id': self.order_id.company_id.id,
        }
