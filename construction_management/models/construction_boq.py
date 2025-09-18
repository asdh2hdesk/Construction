from odoo import models, fields, api


class ConstructionBOQ(models.Model):
    _name = 'construction.boq'
    _description = 'Bill of Quantity'

    name = fields.Char(string='BOQ Item No.', required=True)
    project_id = fields.Many2one('construction.project', string='Project', required=True)
    parent_id = fields.Many2one('construction.boq', string='Parent BOQ', domain="[('project_id', '=', project_id)]")
    child_ids = fields.One2many('construction.boq', 'parent_id', string='Child BOQ Items')

    material_id = fields.Many2one('product.product', string='Material')
    quantity = fields.Float(string='Quantity')
    unit = fields.Char(string='Unit')
    unit_price = fields.Float(string='Unit Price')
    total_price = fields.Float(string='Total Price', compute='_compute_total', store=True)

    labor_hours = fields.Float(string='Labor Hours')
    labor_cost = fields.Float(string='Labor Cost')
    # inventory_id = fields.Many2one('construction.inventory', string='Inventory')

    @api.depends('quantity', 'unit_price', 'child_ids.total_price')
    def _compute_total(self):
        for rec in self:
            if rec.child_ids:
                # If it has children, total = sum of all children's total
                rec.total_price = sum(child.total_price for child in rec.child_ids)
            else:
                # If no children, total = quantity * unit_price
                rec.total_price = rec.quantity * rec.unit_price

