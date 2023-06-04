from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class InheritAccountMove(models.Model):

    _inherit = 'account.move'
    _description = 'Account Move'


    tag_ids = fields.Many2many('template.tag', string='Tag', compute='compute_fields_value')
    tag_ids_name = fields.Char(string='Tag Name', related='tag_ids.name')
    for_ids = fields.Many2many('res.company', string='For ID', compute='compute_fields_value')
    for_ids_name = fields.Char(string='For Name', related='for_ids.name')



    def compute_fields_value(self):
        for rec in self:
            po_domain = [('name','=',rec.ref)]
            po_search = self.env['purchase.order'].search(po_domain)
            so_search = self.env['sale.order'].search(po_domain)

            if po_search:
                rec.tag_ids = po_search.tag_ids
                rec.for_ids = po_search.for_ids

            elif so_search:
                rec.tag_ids = so_search.tag_ids
                rec.for_ids = so_search.for_ids
            else:
                rec.tag_ids = [(5, 0, 0)]
                rec.for_ids = [(5, 0, 0)]




class InheritAccountMove(models.Model):

    _inherit = 'account.move.line'


    for_ids_name = fields.Char(string='For Name', related='move_id.for_ids_name')



class InheritAccountBankStatment(models.Model):

    _inherit = 'account.bank.statement'




    name = fields.Char(string="Name", default=lambda self:self.env['ir.sequence'].next_by_code('cash.journal') or _("Cash Journal"), readonly=True)




