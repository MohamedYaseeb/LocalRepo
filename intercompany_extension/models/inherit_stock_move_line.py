from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InheritStockMoveLine(models.Model):

    _inherit = "stock.move.line"



    po_comment = fields.Char(string="Branch Comment", related='move_id.po_comment')


    # @api.onchange('qty_done')
    # def set_move_quantities(self):
    #     for rec in self:
    #         rec.product_uom_qty = rec.qty_done




class InheritStockMove(models.Model):

    _inherit = "stock.move"



    po_comment = fields.Char(string="Branch Comment", compute='compute_comment')






    def compute_comment(self):
        for rec in self:
            origin_po = self.env['purchase.order'].search([('name','=',rec.origin)])
            origin_so = self.env['sale.order'].search([('name','=',rec.origin)])

            vals_dic = {}
            so_vals_dic = {}
            if origin_po:
                for lines in origin_po.order_line:
                    vals_dic.update({lines.product_id : (lines.product_qty, lines.po_comment)})
                if rec.product_id in vals_dic :
                    rec.po_comment = vals_dic[rec.product_id][1]
                else:
                    rec.po_comment = ""
            elif origin_so:
                for lines in origin_so.order_line:
                    so_vals_dic.update({lines.product_id : (lines.product_uom_qty, lines.po_comment)})
                if rec.product_id in so_vals_dic :
                    rec.po_comment = so_vals_dic[rec.product_id][1]

                else:
                    rec.po_comment = ""

            else:
                rec.po_comment = ""
