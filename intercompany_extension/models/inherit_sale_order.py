# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare, float_round



class InheritSaleorder(models.Model):

    _inherit = "sale.order"





    tag_ids = fields.Many2many('template.tag', string="Tag", compute='compute_po_tags')
    for_ids = fields.Many2many('res.company', string='For ID',  compute='compute_po_tags', check_company=False)
    tag_ids_name = fields.Char(string="Tag ID", related='tag_ids.name')
    for_ids_name = fields.Char(string="For : ", related='for_ids.name')
    second_auto_generated = fields.Boolean(string='Auto Generated Purchase Order', copy=False, default=False)
    auto_generated = fields.Boolean(string='Auto Generated Purchase Order', default=False)
    auto_po_name = fields.Char()
    auto_purchase_order_id = fields.Many2one('purchase.order', string='Source Purchase Order', readonly=True, copy=False)
    delivery_counted = fields.Integer(string='Delivery Orders', compute='compute_picking_ids')




    def compute_picking_ids(self):
        for rec in self:
            deliverys = self.env['stock.picking'].sudo().search([('generated_id_no','=',rec.id)])
            rec.delivery_counted = len(deliverys)




    # @api.onchange('purchase_order_template_id')
    def compute_po_tags(self):
        for rec in self:
            if rec.auto_generated == True:
                    rec.tag_ids = rec.auto_purchase_order_id.tag_ids
                    rec.for_ids = rec.auto_purchase_order_id.for_ids

            else:
                rec.tag_ids = [(5, 0, 0)]
                rec.for_ids = [(5, 0, 0)]






class InheritSaleorderLine(models.Model):

    _inherit = "sale.order.line"

    vendor_price = fields.Monetary(string='Price')
    po_comment = fields.Char(string="Branch Comment")


