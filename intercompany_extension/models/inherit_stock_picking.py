from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import random


class InheritStockPicking(models.Model):

    _inherit = 'stock.picking'



    tag_ids = fields.Many2many('template.tag', string='Tag', compute='compute_fields_value')
    tag_ids_name = fields.Char(string='Tag', related='tag_ids.name')
    for_ids = fields.Many2many('res.company', string='For ID', compute='compute_fields_value')
    for_ids_name = fields.Char(string='For ID', compute='compute_fields_value')
    auto_generated = fields.Boolean(default=False, compute='compute_fields_value')
    branch_generated = fields.Boolean(default=False, compute='compute_fields_value')
    po_comment = fields.Char(string="Branch Comment", compute='compute_comment')
    visibil_state = fields.Boolean(compute='compute_fields_value')
    origin_generator = fields.Char(string="Origin Generator")
    generate_state = fields.Boolean(compute='compute_fields_value', string="Define Generate Transfer Button View state")
    generate_is_clicked = fields.Boolean(default=False)
    generated_id_no = fields.Integer(string="Generated ID")






    def compute_fields_value(self):
        for rec in self:
            order_domain = [('name','=',rec.origin)]
            po_search = self.env['purchase.order'].sudo().search(order_domain)
            so_search = self.env['sale.order'].sudo().search(order_domain)
            so_po_search = self.env['purchase.order'].search([('id','=', so_search.auto_purchase_order_id.id)])
            #Compute Tag ID and For ID  from Source SO or PO
            if po_search:
                rec.auto_generated = po_search.auto_generated
                rec.tag_ids = po_search.sudo().tag_ids
                rec.for_ids = po_search.sudo().for_ids
                rec.for_ids_name = rec.for_ids.name
                rec.visibil_state = False
                rec.generate_state = False
                if po_search.purchase_order_template_id :
                    rec.branch_generated = True
                else:
                    rec.branch_generated = False


            elif so_search:
                rec.tag_ids = so_search.sudo().tag_ids
                rec.for_ids = so_search.sudo().for_ids
                rec.for_ids_name = rec.for_ids.name
                rec.auto_generated = so_search.auto_generated
                rec.branch_generated = False
                if so_po_search.purchase_order_template_id.target_partner_id or so_search.second_auto_generated == True :
                    rec.visibil_state = True
                    rec.generate_state = False

                elif so_po_search.purchase_order_template_id and not so_po_search.purchase_order_template_id.target_partner_id:
                    rec.visibil_state = False
                    rec.generate_state = True
                else:
                    rec.visibil_state = False
                    rec.generate_state = False
            elif rec.origin_generator:
                rec.branch_generated = False
                rec.visibil_state = True
                rec.generate_state = False
                rec.auto_generated = False
                rec.tag_ids = [(5, 0, 0)]
                rec.for_ids = [(5, 0, 0)]
                rec.for_ids_name = self.env['stock.picking'].search([('name','=',rec.origin_generator)]).for_ids_name
            else:
                rec.tag_ids = [(5, 0, 0)]
                rec.for_ids = [(5, 0, 0)]
                rec.for_ids_name = ''
                rec.auto_generated = False
                rec.branch_generated = False
                rec.visibil_state = False
                rec.generate_state = False





    def set_move_quantities(self):
        for rec in self:
            ## Gathering Move Related  SO Info
            origin_so_domain = [('name', '=', rec.origin)]
            origin_move_domain = [('origin', '=', rec.origin)]
            origin_so = self.env['sale.order'].sudo().search(origin_so_domain)
            origin_so_stock_move = self.env['stock.move'].sudo().search(origin_move_domain)
            origin_so_move = self.env['stock.picking'].sudo().search(origin_move_domain)

            # As Move is Originated By Second Generated SO - HQ PO Generated this SO and Branch PO Generated HQ PO Informathion Can be Gathered
            if self.env.user.quantity_validator == True:
                if origin_so and origin_so.second_auto_generated == True:
                    # HQ PO to Factory
                    hq_po_domain = [('name', '=', origin_so.auto_purchase_order_id.name)]
                    hq_po = self.env['purchase.order'].sudo().search(hq_po_domain)
                    # HQ PO Move
                    hq_po_move_domain = [('origin', '=', hq_po.name)]
                    hq_po_move = self.env['stock.picking'].sudo().search(hq_po_move_domain)

                    # Branch PO to HQ
                    branch_po = hq_po.source_po_id
                    # Branch PO to HQ Moves
                    branch_po_move_domain = [('origin', '=', branch_po.name)]
                    branch_po_move = self.env['stock.picking'].sudo().search(branch_po_move_domain)

                    # HQ SO to Branch
                    hq_so_domain = [('auto_purchase_order_id', '=', branch_po.id)]
                    hq_so = self.env['sale.order'].sudo().search(hq_so_domain)
                    # HQ SO to Branch Moves
                    hq_so_domain = [('origin', '=', hq_so.name)]
                    hq_so_move = self.env['stock.picking'].sudo().search(hq_so_domain)

                    values_dictionary = {}
                    if rec.move_ids_without_package:
                        for ids in rec.move_ids_without_package.sudo():
                            values_dictionary.update(
                                {ids.product_id: (ids.quantity_done, ids.product_uom_qty, ids.po_comment)})

                        if rec.move_line_ids_without_package:
                            for my_line in rec.move_line_ids_without_package.sudo():
                                if my_line.product_id in values_dictionary:
                                    my_line.product_uom_qty = values_dictionary[my_line.product_id][1]
                            rec.sudo().state = 'assigned'
                            # origin_so.invoice_status = 'to invoice'

                        if origin_so.order_line:
                            for orders in origin_so.order_line.sudo():
                                if orders.product_id in values_dictionary:
                                    orders.sudo().qty_delivered = values_dictionary[orders.product_id][0]
                                    orders.sudo().product_uom_qty = values_dictionary[orders.product_id][1]



                        if hq_po_move.move_ids_without_package:
                            for lines in hq_po_move.move_ids_without_package.sudo():
                                if lines.product_id in values_dictionary:
                                    lines.sudo().quantity_done = values_dictionary[lines.product_id][0]
                                    lines.sudo().product_uom_qty = values_dictionary[lines.product_id][1]

                        if hq_so_move.move_ids_without_package:
                            for lin in hq_so_move.move_ids_without_package.sudo():
                                if lin.product_id in values_dictionary:
                                    lin.sudo().quantity_done = values_dictionary[lin.product_id][0]
                                    lin.sudo().product_uom_qty = values_dictionary[lin.product_id][1]


                        if hq_so_move.move_line_ids_without_package:
                            for lin_2 in hq_so_move.move_line_ids_without_package.sudo():
                                if lin_2.sudo().product_id in values_dictionary:
                                    lin_2.sudo().product_uom_qty = values_dictionary[lin_2.product_id][1]
                                    lin_2.sudo().qty_done = values_dictionary[lin_2.product_id][1]
                            hq_so_move.sudo().state = 'assigned'

                        if hq_so.order_line:
                            for orders in hq_so.order_line.sudo():
                                if orders.product_id in values_dictionary:
                                    orders.sudo().product_uom_qty = values_dictionary[orders.product_id][0]
                                    orders.sudo().qty_delivered = values_dictionary[orders.product_id][0]


                        if branch_po_move.move_ids_without_package:
                            for line in branch_po_move.move_ids_without_package.sudo():
                                if line.sudo().product_id in values_dictionary:
                                    line.sudo().quantity_done = values_dictionary[line.product_id][0]




                elif rec.origin_generator != False and rec.picking_type_id.code == 'internal':
                    move_values = {}

                    orign_so_domain = [('id','=', rec.generated_id_no)]
                    hq_so = self.env['sale.order'].sudo().search(orign_so_domain)
                    branch_po = self.env['purchase.order'].sudo().search([('id','=', hq_so.auto_purchase_order_id.id)])
                    hq_so_move = self.env['stock.picking'].sudo().search([('origin','=',hq_so.name)])
                    branch_po_move = self.env['stock.picking'].sudo().search([('origin','=',branch_po.name)])

                    if rec.move_ids_without_package:
                        for ids in rec.move_ids_without_package.sudo():
                            move_values.update({ids.product_id: (ids.quantity_done, ids.product_uom_qty, ids.po_comment)})

                        if rec.move_line_ids_without_package:
                            for moves in rec.sudo().move_line_ids_without_package:
                                if moves.sudo().product_id in move_values:
                                    moves.sudo().product_uom_qty = move_values[moves.product_id][1]
                            rec.sudo().state = 'assigned'


                        if hq_so and hq_so_move:
                            for moves in hq_so_move.sudo().move_ids_without_package:
                                if moves.product_id in move_values:
                                    moves.sudo().product_uom_qty = move_values[moves.product_id][1]
                                    moves.sudo().quantity_done = move_values[moves.product_id][0]
                                    moves.sudo().po_comment = move_values[moves.product_id][2]
                            for moves in hq_so_move.sudo().move_line_ids_without_package:
                                if moves.product_id in move_values:
                                    moves.sudo().product_uom_qty = move_values[moves.product_id][1]
                                    moves.sudo().qty_done = move_values[moves.product_id][0]
                                    moves.sudo().po_comment = move_values[moves.product_id][2]
                                hq_so_move.sudo().state = 'assigned'

                            for orders in hq_so.sudo().order_line:
                                if orders.product_id in move_values:
                                    orders.sudo().qty_delivered = move_values[orders.product_id][0]
                                    orders.sudo().product_uom_qty = move_values[orders.product_id][1]

                        if branch_po and branch_po_move:
                            for moves in branch_po_move.sudo().move_ids_without_package:
                                if moves.product_id in move_values:
                                    moves.sudo().product_uom_qty = move_values[moves.product_id][1]
                                    moves.sudo().quantity_done = move_values[moves.product_id][0]
                                    moves.sudo().po_comment = move_values[moves.product_id][2]
                            for moves in branch_po_move.sudo().move_line_ids_without_package:
                                if moves.product_id in move_values:
                                    moves.sudo().product_uom_qty = move_values[moves.product_id][1]
                                    moves.sudo().qty_done = move_values[moves.product_id][0]
                                    moves.sudo().po_comment = move_values[moves.product_id][2]
                                branch_po_move.sudo().state = 'assigned'




                elif origin_so and origin_so.sudo().auto_generated== True and origin_so.sudo().second_auto_generated == False :
                    # Related PO
                    po_domain = [('name', '=', origin_so.auto_purchase_order_id.name)]
                    related_po = self.env['purchase.order'].sudo().search(po_domain)
                    # Related PO Move
                    related_po_move_domain = [('origin', '=', related_po.name)]
                    related_po_move = self.env['stock.picking'].sudo().search(related_po_move_domain)

                    dic_vals = {}
                    if rec.move_ids_without_package:
                        for ids in rec.move_ids_without_package.sudo():
                            dic_vals.update({ids.product_id: (ids.quantity_done, ids.product_uom_qty, ids.po_comment)})

                        if rec.move_line_ids_without_package:

                            for rela_lines in rec.sudo().move_ids_without_package.sudo():
                                if rela_lines.product_id in dic_vals:
                                    rela_lines.sudo().product_uom_qty = dic_vals[rela_lines.product_id][1]

                            for relat_lines in rec.sudo().move_line_ids_without_package:
                                if relat_lines.product_id in dic_vals:
                                    relat_lines.sudo().product_uom_qty = dic_vals[relat_lines.product_id][1]
                            rec.sudo().state = 'assigned'

                        if origin_so.sudo().order_line:
                            for orders in origin_so.sudo().order_line:
                                if orders.product_id in dic_vals:
                                    orders.sudo().qty_delivered = dic_vals[orders.product_id][0]
                                    orders.sudo().product_uom_qty = dic_vals[orders.product_id][1]


                        if related_po_move.sudo().move_ids_without_package:
                            for rel_lines in related_po_move.sudo().move_ids_without_package:
                                if rel_lines.product_id in dic_vals:
                                    rel_lines.sudo().quantity_done = dic_vals[rel_lines.product_id][0]
                                    rel_lines.sudo().product_uom_qty = dic_vals[rel_lines.product_id][1]


            else:
                raise ValidationError(_("You are Not Allowed to Set Quantities"))





    def button_validate(self):
        for rec in self:
            origin_domain = [('name', '=', rec.origin)]
            origin_po = self.env['purchase.order'].sudo().search(origin_domain)
            origin_so = self.env['sale.order'].sudo().search(origin_domain)


            if rec.generated_id_no and rec.picking_type_id.code == 'internal':

                if self.env.user.property_warehouse_id == rec.location_dest_id.warehouse_id:
                    rec.state = 'done'
                    # related_so = self.env['sale.order'].sudo().browse(rec.generated_id_no)
                    # related_so_picking = self.env['stock.picking'].sudo().search([('origin', '=', related_so.name)])

                else:
                    raise ValidationError(_("You are Not Allowed to Validate Order"))


            elif origin_po:
                so_domain = [('auto_purchase_order_id', '=', origin_po.id)]
                related_so = self.env['sale.order'].sudo().search(so_domain)
                related_so_picking = self.env['stock.picking'].sudo().search([('origin', '=', related_so.name)])


                if origin_po.purchase_order_template_id.target_partner_id or origin_po.second_auto_generated == True :
                    if self.env.user.delivery_validator == True:
                        related_so_picking.state = 'done'
                    elif self.env.user.delivery_validator == False:
                        raise ValidationError(_("You are Not Authorized to Validate Order"))

                elif origin_po.purchase_order_template_id and not origin_po.purchase_order_template_id.target_partner_id:
                    if self.env.user.delivery_validator == True:
                        related_so_picking.state = 'done'
                        # related_so_int_picking.state = 'done'

                    elif self.env.user.delivery_validator == False:
                        raise ValidationError(_("You are Not Authorized to Validate Order"))



            elif origin_so and origin_so.auto_generated == True:
                raise ValidationError(_("Validating Order from SO is Not Allowed"))





            else:
                continue
        return super(InheritStockPicking, self).button_validate()






    def generate_internal_transfer(self):
        for rec in self:
            rec.generate_is_clicked = True
            source_document = rec.origin
            source_so = self.env['sale.order'].sudo().search([('name', '=', source_document)])
            source_so_po = self.env['purchase.order'].sudo().search([('partner_ref', '=', source_so.name)])
            source_po_pick = self.env['stock.picking'].sudo().search([('origin', '=', source_so.name)])

            if source_so and source_so.auto_generated == True:
                if source_so_po.purchase_order_template_id and not source_so_po.purchase_order_template_id.target_partner_id:
                    alternate_company_location = self.env['stock.location'].sudo().search(
                        [('usage', '=', 'internal'), ('company_id', '=', rec.location_id.company_id.id),('name','!=',rec.location_id.name)])
                    stock_pick_type = self.env['stock.picking.type'].sudo().search(
                        [('code', '=', 'internal'), ('company_id', '=', rec.location_id.company_id.id),('warehouse_id','!=',rec.location_id.warehouse_id.id)])

                    if alternate_company_location and stock_pick_type:
                        stock_id_list = []
                        unique_name = self.env['ir.sequence'].next_by_code('stock.picking')
                        for line in rec.move_ids_without_package.sudo():
                            self.sudo().env['stock.move'].create({
                                'product_id': line.product_id.id,
                                'name': unique_name,
                                'reference': unique_name,
                                'product_uom_qty': line.product_uom_qty,
                                'reserved_availability': line.product_uom_qty,
                                'product_uom': line.product_id.uom_id.id,
                                'location_id': alternate_company_location[0].id,
                                'location_dest_id': line.location_id.id,
                                'company_id': line.company_id.id,
                            })
                            stock_search_move = self.env['stock.move'].sudo().search([('reference', '=', unique_name)])
                            for stock_move_item in stock_search_move:
                                stock_id_move = stock_move_item.id
                            stock_id_list.append(stock_id_move)

                        self.sudo().create({
                            'name': unique_name,
                            'for_ids_name': self.for_ids_name,
                            'tag_ids_name': self.tag_ids_name,
                            'partner_id': '',
                            'generated_id_no': self.generated_id_no,
                            'location_id': alternate_company_location[0].id,
                            'location_dest_id': rec.location_id.id,
                            'picking_type_id': stock_pick_type.id,
                            'origin_generator': rec.name,
                            'move_ids_without_package': [(6, 0, stock_id_list)],
                        })

                    elif not alternate_company_location:
                        raise ValidationError(_("Vendor Has No Other Stock Locations to Process Internal Transfer as Quotation Template Suggests, Create New Location or Deselect Template "))

                    else:
                        raise ValidationError(_(" Vendor Second Warehouse Has No Internal Transfer Operation Type"))




    @api.model
    def create(self, vals):
        origin = vals.get('origin')
        if origin:
            so_domain = [('name', '=', origin)]
            so_order = self.env['sale.order'].sudo().search(so_domain)
            vals['generated_id_no'] = so_order.id


        return super(InheritStockPicking, self).create(vals)








class InheritStockBacOrderConfirmation(models.TransientModel):

    _inherit = 'stock.backorder.confirmation'

    def validated_process(self):
        pickings_to_do = self.env['stock.picking']
        pickings_not_to_do = self.env['stock.picking']
        for line in self.backorder_confirmation_line_ids:
            if line.to_backorder is True:
                pickings_to_do |= line.picking_id
            else:
                pickings_not_to_do |= line.picking_id

        for pick_id in pickings_not_to_do:
            moves_to_log = {}
            for move in pick_id.move_lines:
                if float_compare(move.product_uom_qty,
                                 move.quantity_done,
                                 precision_rounding=move.product_uom.rounding) > 0:
                    moves_to_log[move] = (move.quantity_done, move.product_uom_qty)
            pick_id._log_less_quantities_than_expected(moves_to_log)

        pickings_to_validate = self.env.context.get('button_validate_picking_ids')
        if pickings_to_validate:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate).with_context(skip_backorder=True)
            if pickings_not_to_do:
                pickings_to_validate = pickings_to_validate.with_context(picking_ids_not_to_backorder=pickings_not_to_do.ids)
            if self.env.user.has_group('base.group_erp_manager'):
                return pickings_to_validate.button_validate()
            else:
                raise ValidationError(_("You are Not Allowed to Perform Backorders"))
        return True