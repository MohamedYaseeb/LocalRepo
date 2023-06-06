from odoo import models, fields, api, _
import datetime


class InheritStockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"
    _description = 'Inherit Stock Valuation'

    origin_document = fields.Char(string='Source Document', related='stock_move_id.origin')
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    cost_price = fields.Float(string="Cost Price", related='product_id.standard_price')
    list_price = fields.Float(string="Sale Price", related='product_id.list_price')
    total_list_price = fields.Float(string='Total Sale Price', compute='_compute_total_sale')
    partner_name = fields.Char(string='Customer / Vendor', compute='get_origin_data')
    invoice_name = fields.Char(string="Invoice", compute='get_origin_data')
    lot_name = fields.Char(string='Lot')
    expiration_date = fields.Char(string='Expiry Date')
    is_bonus = fields.Boolean(string="Is Bonus", compute='get_origin_data')
    is_so = fields.Float(string='is SO')
    is_po = fields.Float(string='is PO')

    @api.depends('list_price')
    def _compute_total_sale(self):
        for rec in self:
            rec.total_list_price = rec.list_price * rec.quantity

    @api.depends('origin_document')
    def get_origin_data(self):
        for rec in self:
            domain = [('name', '=', rec.origin_document)]
            acc_domain = [('invoice_origin', '=', rec.origin_document)]
            PO_group = self.env['purchase.order'].read_group(domain=domain, fields=['partner_id'],
                                                             groupby=['partner_id'])
            PO_group_name = self.env['purchase.order'].search(domain)
            SO_group = self.env['sale.order'].read_group(domain=domain, fields=['partner_id'], groupby=['partner_id'])
            SO_group_name = self.env['sale.order'].search(domain)
            acc_obj = self.env['account.move'].read_group(fields=['name'], domain=acc_domain, groupby=['name'])
            stock_domain = [('origin', '=', rec.origin_document)]
            SML_search = self.env['stock.move.line'].search(stock_domain)
            SP_search = self.env['stock.picking'].search([('origin', '=', rec.origin_document)])

            lot_list = []
            expiry_list = []
            str_list = []



            if SP_search and PO_group:
                for stock_move_lines in SP_search.move_ids_without_package:
                    if stock_move_lines.product_id.id == rec.product_id.id:
                        if stock_move_lines.quantity_done == rec.quantity:
                            rec.is_po = rec.quantity
                            for lots in stock_move_lines.lot_ids:
                                lot_list.append(lots.name)
                                expiry_list.append(lots.expiration_date)
                                lot_list = list(dict.fromkeys(lot_list))
                                expiry_list = list(dict.fromkeys(expiry_list))
                                rec.lot_name = lot_list
                            for dates in expiry_list:
                                if dates:
                                    str_date = datetime.datetime.strftime(dates, '%m/%y')
                                    str_list.append(str_date)
                                    str_list = list(dict.fromkeys(str_list))
                                    rec.expiration_date = str_list
                                else:
                                    rec.expiration_date = ''


            elif SP_search and SO_group:
                for stock_move_lines in SP_search.move_ids_without_package:
                    if stock_move_lines.product_id.id == rec.product_id.id:
                        if stock_move_lines.quantity_done == rec.quantity * - 1:
                            rec.is_so = rec.quantity
                            for lots in stock_move_lines.lot_ids:
                                lot_list.append(lots.name)
                                expiry_list.append(lots.expiration_date)
                                rec.lot_name = lot_list
                            for dates in expiry_list:
                                if dates:
                                    str_date = datetime.datetime.strftime(dates, '%m/%y')
                                    str_list.append(str_date)
                                    rec.expiration_date = str_list
                                else:
                                    rec.expiration_date = ''



            else:
                rec.lot_name = ''
                rec.expiration_date = ''

            # for stock_move_lines in SML_search:
            #     if SML_search and SO_group:
            #         if stock_move_lines.product_id.id == rec.product_id.id:
            #             if stock_move_lines.qty_done == rec.quantity * -1:
            #                 rec.lot_name = stock_move_lines.lot_id.name
            #                 rec.is_so = rec.quantity
            #                 if stock_move_lines.lot_id.expiration_date:
            #                     date_time = stock_move_lines.lot_id.expiration_date
            #                     str_date = datetime.datetime.strftime(date_time, '%m/%y')
            #                     rec.expiration_date = str_date
            #                 else:
            #                     rec.expiration_date = ''
            #             else:
            #                 rec.is_so = rec.quantity
            #                 for lots in stock_move_lines:
            #                     lot_list.append(lots.lot_id.name)
            #                     expiry_list.append(lots.lot_id.expiration_date)
            #                     lot_list = list(dict.fromkeys(lot_list))
            #                     expiry_list = list(dict.fromkeys(expiry_list))
            #                 for dates in expiry_list:
            #                     str_date = datetime.datetime.strftime(dates, '%m/%y')
            #                     str_list.append(str_date)
            #                     str_list = list(dict.fromkeys(str_list))
            #                 rec.lot_name = lot_list
            #                 rec.expiration_date = str_list
            #
            #
            #     elif SML_search and PO_group:
            #         if stock_move_lines.product_id.id == rec.product_id.id:
            #             if stock_move_lines.qty_done == rec.quantity:
            #                 rec.lot_name = stock_move_lines.lot_id.name
            #                 rec.is_po = rec.quantity
            #                 if stock_move_lines.lot_id.expiration_date:
            #                     date_time = stock_move_lines.lot_id.expiration_date
            #                     str_date = datetime.datetime.strftime(date_time, '%m/%y')
            #                     rec.expiration_date = str_date
            #                 else:
            #                     rec.expiration_date = ''
            #             else:
            #                 rec.is_po = rec.quantity
            #                 for lots in stock_move_lines:
            #                     lot_list.append(lots.lot_id.name)
            #                     expiry_list.append(lots.lot_id.expiration_date)
            #                     lot_list = list(dict.fromkeys(lot_list))
            #                     expiry_list = list(dict.fromkeys(expiry_list))
            #                 for dates in expiry_list:
            #                     str_date = datetime.datetime.strftime(dates, '%m/%y')
            #                     str_list.append(str_date)
            #                     str_list = list(dict.fromkeys(str_list))
            #                 rec.lot_name = lot_list
            #                 rec.expiration_date = str_list
            #     else:
            #         rec.lot_name = ''
            #         rec.expiration_date = ''
            #         rec.is_so = 0
            #         rec.is_po = 0

            ## Invoice Name
            if acc_obj:
                rec.invoice_name = acc_obj[0]['name']

            else:
                rec.invoice_name = ''

            ## Partner Name - RES PARTNER MODEL ###
            if PO_group:
                partner_n = PO_group[0]['partner_id'][0]
                browse_partner = self.env['res.partner'].browse(partner_n)
                rec.partner_name = browse_partner.name
                for order_line in PO_group_name.order_line:
                    if order_line.product_id.id == rec.product_id.id:
                        if order_line.product_qty == rec.quantity:
                            rec.is_bonus = order_line.is_bonus
                        else:
                            rec.is_bonus = False


            elif SO_group:
                partner_n = SO_group[0]['partner_id'][0]
                browse_partner = self.env['res.partner'].browse(partner_n)
                rec.partner_name = browse_partner.name
                sale_order_name = SO_group_name
                for s_order_line in sale_order_name.order_line:
                    if s_order_line.product_id.id == rec.product_id.id:
                        if s_order_line.qty_invoiced == rec.quantity * -1:
                            rec.is_bonus = s_order_line.is_bonus
                        else:
                            rec.is_bonus = False

            else:
                rec.partner_name = ''
                rec.is_bonus = False
