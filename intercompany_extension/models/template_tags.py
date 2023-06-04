from odoo import models, fields, api, _



class PurchaceTemplateTag(models.Model):

    _name = 'template.tag'
    _description = 'Purchase Template Tags'


    name = fields.Char(string='Name')
    color = fields.Char(string='Color')





class PoSInheritance(models.Model):

    _inherit = 'pos.config'



    def _get_group_pos_manager(self):
        return self.env.ref('point_of_sale.group_pos_user')

    def _get_group_pos_user(self):
        return self.env.ref('point_of_sale.group_pos_user')


    group_pos_manager_id = fields.Many2one('res.groups', string='Point of Sale Manager Group', default=_get_group_pos_user,
        help='This field is there to pass the id of the pos manager group to the point of sale client.')
    group_pos_user_id = fields.Many2one('res.groups', string='Point of Sale User Group', default=_get_group_pos_user,
        help='This field is there to pass the id of the pos user group to the point of sale client.')



