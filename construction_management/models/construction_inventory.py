from odoo import models, fields, api


class ConstructionInventory(models.Model):
    _name = 'construction.inventory'
    _description = 'Construction Inventory'
    _rec_name = 'material_id'

    material_id = fields.Many2one('product.product', string='Material', required=True)
    project_id = fields.Many2one('construction.project', string='Project')

    # Stock Information
    current_stock = fields.Float(string='Current Stock', default=0.0)
    allocated_qty = fields.Float(string='Allocated Quantity', compute='_compute_allocated_qty', store=True)
    available_qty = fields.Float(string='Available Quantity', compute='_compute_available_qty', store=True)

    # BOQ Information
    total_required = fields.Float(string='Total Required', compute='_compute_total_required', store=True)

    # Cost Information
    unit = fields.Char(string='Unit')
    unit_cost = fields.Float(string='Unit Cost')
    total_value = fields.Float(string='Total Value', compute='_compute_total_value', store=True)

    # Status
    stock_status = fields.Selection([
        ('adequate', 'Adequate Stock'),
        ('low', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('over_stock', 'Over Stock')
    ], string='Stock Status', compute='_compute_stock_status', store=True)

    boq_ids = fields.One2many('construction.boq', 'material_id', string='BOQ References')

    @api.depends('material_id')
    def _compute_boq_ids(self):
        for rec in self:
            rec.boq_ids = self.env['construction.boq'].search([('material_id', '=', rec.material_id.id)])

    @api.depends('material_id', 'project_id')
    def _compute_total_required(self):
        """Compute total required based on BOQ items"""
        for rec in self:
            total = 0.0
            if rec.material_id:
                # Get all BOQ items for this material
                boq_domain = [('material_id', '=', rec.material_id.id)]

                # If project is specified, filter by project
                if rec.project_id:
                    boq_domain.append(('project_id', '=', rec.project_id.id))

                boq_items = self.env['construction.boq'].search(boq_domain)
                total = sum(boq_items.mapped('quantity'))

                # _logger.info(
                #     f"Material {rec.material_id.name}: Found {len(boq_items)} BOQ items, total required: {total}")

            rec.total_required = total

    @api.depends('current_stock', 'total_required')
    def _compute_allocated_qty(self):
        for rec in self:
            if rec.total_required > 0:
                rec.allocated_qty = min(rec.current_stock, rec.total_required)
            else:
                rec.allocated_qty = 0.0

    @api.depends('current_stock', 'allocated_qty')
    def _compute_available_qty(self):
        for rec in self:
            rec.available_qty = rec.current_stock - rec.allocated_qty

    @api.depends('current_stock', 'unit_cost')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = rec.current_stock * rec.unit_cost

    @api.depends('current_stock', 'total_required')
    def _compute_stock_status(self):
        for rec in self:
            if rec.current_stock == 0:
                rec.stock_status = 'out_of_stock'
            elif rec.current_stock < rec.total_required:
                rec.stock_status = 'low'
            elif rec.current_stock > rec.total_required * 1.2:  # 20% buffer
                rec.stock_status = 'over_stock'
            else:
                rec.stock_status = 'adequate'

    def recompute_values(self):
        """Manually trigger recomputation of all computed fields"""
        self._compute_total_required()
        self._compute_allocated_qty()
        self._compute_available_qty()
        self._compute_total_value()
        self._compute_stock_status()
        return True

    def get_project_boq_items(self):
        """Get BOQ items for current project only"""
        if not self.project_id:
            return self.boq_ids
        return self.boq_ids.filtered(lambda x: x.project_id.id == self.project_id.id)

    def action_view_boq_items(self):
        """View BOQ items for this material and project"""
        domain = [('material_id', '=', self.material_id.id)]

        # Add project filter if project is selected
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': f'BOQ Items - {self.material_id.name}',
            'res_model': 'construction.boq',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'default_material_id': self.material_id.id,
                'default_project_id': self.project_id.id if self.project_id else False,
                'default_unit_price': self.unit_cost,
            }
        }

    def write(self, vals):
        result = super().write(vals)
        # If material_id or project_id changed, recompute values
        if 'material_id' in vals or 'project_id' in vals or 'current_stock' in vals:
            self.recompute_values()
        return result