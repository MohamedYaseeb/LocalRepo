# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_purchase_order_template = fields.Boolean(
        "Purchase Quotation Templates", implied_group='sale_management.group_sale_order_template')
    company_so_template_id = fields.Many2one(
        related="company_id.purchase_order_template_id", string="Default Template", readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")



    def set_values(self):
        if not self.group_purchase_order_template:
            self.company_so_template_id = None
            self.env['res.company'].sudo().search([]).write({
                'purchase_order_template_id': False,
            })
        return super(ResConfigSettings, self).set_values()






class PoSConfigInheritance(models.Model):


    _inherit = 'pos.config'


    def get_group_pos_manager(self):
        return self.env.ref('point_of_sale.group_pos_user')

    def get_group_pos_user(self):
        return self.env.ref('point_of_sale.group_pos_user')




    group_pos_manager_id = fields.Many2one('res.groups', string='Point of Sale Manager Group', default=get_group_pos_manager,
        help='This field is there to pass the id of the pos manager group to the point of sale client.')
    group_pos_user_id = fields.Many2one('res.groups', string='Point of Sale User Group', default=get_group_pos_user,
        help='This field is there to pass the id of the pos user group to the point of sale client.')


