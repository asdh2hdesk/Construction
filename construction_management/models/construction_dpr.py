from odoo import models, fields, api


class ConstructionDPR(models.Model):
    _name = 'construction.dpr'
    _description = 'Daily Progress Report'
    _inherit = "translation.mixin"

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    date = fields.Date(string='Date', default=fields.Date.today)
    project_id = fields.Many2one('construction.project', string='Project', required=True)
    summary = fields.Text(string='Daily Summary', translate=True)
    issues = fields.Text(string='Site Issues', translate=True)
    employee_count = fields.Integer(string="Number of Employees", default=0)
    labor_hours = fields.Float(string='Total Working Hours', compute="_compute_labor_hours", store=True)
    working_hours = fields.Float(string='Working Hours/employee', default=8.0)
    per_cost = fields.Monetary(string='Per Day/employee')
    material_used_ids = fields.One2many('construction.dpr.material', 'dpr_id', string='Materials Used')
    stock_move_ids = fields.One2many(
        'stock.move', 'dpr_material_id',
        string="Stock Moves",
        compute="_compute_stock_moves",
        store=False
    )
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'construction.dpr')],  # Replace with your actual model name
        string='Image Attachments'
    )

    image_filename = fields.Char(string='Image Filename')

    @api.depends('employee_count')
    def _compute_labor_hours(self):
        for rec in self:
            rec.labor_hours = rec.employee_count * 8

    def _compute_stock_moves(self):
        for rec in self:
            rec.stock_move_ids = self.env['stock.move'].search([
                ('dpr_material_id.dpr_id', '=', rec.id)
            ])


class ConstructionDPRMaterial(models.Model):
    _name = 'construction.dpr.material'
    _description = 'Materials Used in DPR'

    dpr_id = fields.Many2one('construction.dpr', string='DPR')
    product_id = fields.Many2one('product.product', string='Material')
    quantity = fields.Float(string='Quantity')
    # uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True)
    unit = fields.Char(string='Unit of Measure')
    # unit_cost = fields.Float(string='Unit Cost', related='product_id.standard_price', readonly=True)
    unit_cost = fields.Float(string='Unit Cost')
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)
    remarks = fields.Text(string='Remarks')

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.quantity * record.unit_cost

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # Auto-create stock move when material is used
        self._create_stock_consumption(rec)
        return rec

    def _create_stock_consumption(self, dpr_material):
        """Create stock consumption move for DPR materials"""
        if dpr_material.quantity <= 0:
            return

        # Get or create source location (stock/internal)
        stock_location = self._get_stock_location()

        # Get or create destination location (production)
        production_location = self._get_production_location()

        # Create stock move
        stock_move = self.env['stock.move'].create({
            'name': f'Material consumption - {dpr_material.dpr_id.project_id.name}',
            'product_id': dpr_material.product_id.id,
            'product_uom_qty': dpr_material.quantity,
            'product_uom': dpr_material.product_id.uom_id.id,
            'location_id': stock_location.id,
            'location_dest_id': production_location.id,
            'construction_project_id': dpr_material.dpr_id.project_id.id,
            'dpr_material_id': dpr_material.id,
        })

        # Confirm and execute the move
        stock_move._action_confirm()
        stock_move._action_done()

        return stock_move

    def _get_stock_location(self):
        """Get stock location with fallback options"""
        # Try standard stock location first
        location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

        if not location:
            # Try to find any internal location
            location = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
                ('active', '=', True)
            ], limit=1)

        if not location:
            # Create a default internal location if none exists
            company_id = self.env.company.id
            location = self.env['stock.location'].create({
                'name': 'Stock',
                'usage': 'internal',
                'location_id': self.env.ref('stock.stock_location_locations').id,
                'company_id': company_id,
            })

        return location

    def _get_production_location(self):
        """Get production location with fallback options"""
        # Try standard production location first
        location = self.env.ref('stock.stock_location_production', raise_if_not_found=False)

        if not location:
            # Try to find any production location
            location = self.env['stock.location'].search([
                ('usage', '=', 'production'),
                ('active', '=', True)
            ], limit=1)

        if not location:
            # Create a production location if none exists
            company_id = self.env.company.id

            # Get or create the locations parent
            locations_parent = self.env.ref('stock.stock_location_locations', raise_if_not_found=False)
            if not locations_parent:
                locations_parent = self.env['stock.location'].search([
                    ('usage', '=', 'view'),
                    ('name', 'ilike', 'locations')
                ], limit=1)

            location = self.env['stock.location'].create({
                'name': 'Production',
                'usage': 'production',
                'location_id': locations_parent.id if locations_parent else False,
                'company_id': company_id,
            })

        return location