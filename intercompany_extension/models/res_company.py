# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError





class ResCompany(models.Model):
    _inherit = "res.company"
    _check_company_auto = True


    purchase_order_template_id = fields.Many2one(
        "purchase.order.template", string="Default Purchase Template",
        domain="['|', ('company_id', '=', False), ('company_id', '=', id)]",
        check_company=True,
    )




class ResUserInheritedCompany(models.Model):


    _inherit = "res.users"


    product_creator = fields.Boolean(string='Product Creator')
    cost_viewer = fields.Boolean(string='Cost Viewer')
    delivery_validator = fields.Boolean(string='Stock Validators')
    quantity_validator = fields.Boolean(string='Quantity Validators')




class InheritProductProduct(models.Model):

        _inherit = 'product.product'



        @api.model_create_multi
        def create(self, vals_list):
            for vals in vals_list:
                self.product_tmpl_id._sanitize_vals(vals)
            products = super(InheritProductProduct ,self.with_context(create_product_product=True)).create(vals_list)
            # `_get_variant_id_for_combination` depends on existing variants
            user_obj = self.env['res.users'].sudo().browse(self.env.uid)
            self.clear_caches()
            if self.env.user.product_creator == True:
                return products
            else:
                raise ValidationError(_('You are Not Allowed To Create Product'))