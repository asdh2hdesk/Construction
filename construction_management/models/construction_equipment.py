from odoo import models, fields, api


class ConstructionEquipmentAllocation(models.Model):
    _name = 'construction.equipment.allocation'
    _description = 'Equipment Allocation to Projects'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Allocation Reference', required=True, default='New', tracking=True, translate=True)
    project_id = fields.Many2one('construction.project', string='Project', required=True, tracking=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Machine Number', required=True, tracking=True)
    construction_task_id = fields.Many2one(
        'project.task.simple',
        string='Task', domain="[('project_id', '=', project_id)]"
    )

    # Allocation details
    allocation_date = fields.Date(string='Allocation Date', default=fields.Date.today, required=True, tracking=True)
    return_date = fields.Date(string='Expected Return Date', tracking=True)
    actual_return_date = fields.Date(string='Actual Return Date', tracking=True)

    # Costing
    hourly_rate = fields.Float(string='Hourly Rate', required=True, tracking=True)
    daily_rate = fields.Float(string='Daily Rate', compute='_compute_daily_rate', store=True)
    total_hours = fields.Float(string='Total Hours Used', default=0.0, tracking=True)
    total_days = fields.Float(string='Total Days Used', compute='_compute_total_days', store=True)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True, tracking=True)
    category = fields.Selection([
        ('owned', 'Owned'),
        ('contractual', 'Contractual')
    ], string='Category', required=True, tracking=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('allocated', 'Allocated'),
        ('in_use', 'In Use'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Usage logs
    usage_log_ids = fields.One2many('construction.equipment.usage', 'allocation_id', string='Usage Logs')
    maintenance_log_ids = fields.One2many('construction.equipment.maintenance', 'allocation_id',
                                          string='Maintenance Logs')

    # Notes
    notes = fields.Text(string='Notes', translate=True)
    operator_name = fields.Many2one('hr.employee', string='Operator Name', tracking=True)

    @api.depends('hourly_rate')
    def _compute_daily_rate(self):
        for record in self:
            record.daily_rate = record.hourly_rate * 8  # 8 hours per day

    @api.depends('allocation_date', 'actual_return_date', 'return_date')
    def _compute_total_days(self):
        for record in self:
            if record.allocation_date:
                end_date = record.actual_return_date or record.return_date or fields.Date.today()
                if end_date >= record.allocation_date:
                    delta = end_date - record.allocation_date
                    record.total_days = delta.days + 1
                else:
                    record.total_days = 0
            else:
                record.total_days = 0

    @api.depends('total_hours', 'hourly_rate', 'total_days', 'daily_rate')
    def _compute_total_cost(self):
        for record in self:
            if record.total_hours > 0:
                record.total_cost = record.total_hours * record.hourly_rate
            else:
                record.total_cost = record.total_days * record.daily_rate

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('construction.equipment.allocation') or 'New'
        return super().create(vals)

    def action_allocate(self):
        self.state = 'allocated'

    def action_start_use(self):
        self.state = 'in_use'

    def action_return(self):
        self.actual_return_date = fields.Date.today()
        self.state = 'returned'

    def action_cancel(self):
        self.state = 'cancelled'


class ConstructionEquipmentUsage(models.Model):
    _name = 'construction.equipment.usage'
    _description = 'Equipment Usage Log'

    allocation_id = fields.Many2one('construction.equipment.allocation', string='Allocation', required=True,
                                    ondelete='cascade')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    hours_used = fields.Float(string='Hours Used', required=True)
    fuel_consumption = fields.Float(string='Fuel Consumption (Liters)')
    operator_name = fields.Char(string='Operator Name')
    work_description = fields.Text(string='Work Description', translate=True)
    remarks = fields.Text(string='Remarks')

    # Computed fields
    equipment_id = fields.Many2one(related='allocation_id.equipment_id', string='Equipment', readonly=True)
    project_id = fields.Many2one(related='allocation_id.project_id', string='Project', readonly=True)
    cost_for_day = fields.Float(string='Cost for Day', compute='_compute_cost_for_day', store=True)

    @api.depends('hours_used', 'allocation_id.hourly_rate')
    def _compute_cost_for_day(self):
        for record in self:
            record.cost_for_day = record.hours_used * record.allocation_id.hourly_rate


class ConstructionEquipmentMaintenance(models.Model):
    _name = 'construction.equipment.maintenance'
    _description = 'Equipment Maintenance Log'

    allocation_id = fields.Many2one('construction.equipment.allocation', string='Allocation', required=True,
                                    ondelete='cascade')
    date = fields.Date(string='Maintenance Date', required=True, default=fields.Date.today)
    maintenance_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective'),
        ('breakdown', 'Breakdown'),
        ('inspection', 'Inspection')
    ], string='Maintenance Type', required=True)

    description = fields.Text(string='Maintenance Description', required=True, translate=True)
    cost = fields.Float(string='Maintenance Cost')
    downtime_hours = fields.Float(string='Downtime Hours')
    technician_name = fields.Char(string='Technician Name', translate=True)
    parts_used = fields.Text(string='Parts Used', translate=True)
    next_maintenance_date = fields.Date(string='Next Maintenance Date')

    # Computed fields
    equipment_id = fields.Many2one(related='allocation_id.equipment_id', string='Equipment', readonly=True)
    project_id = fields.Many2one(related='allocation_id.project_id', string='Project', readonly=True)


# Update the Construction Project model to include equipment costs
class ConstructionProject(models.Model):
    _inherit = 'construction.project'

    equipment_allocation_ids = fields.One2many('construction.equipment.allocation', 'project_id',
                                               string='Equipment Allocations')

    @api.depends('equipment_allocation_ids.total_cost')
    def _compute_equipment_cost(self):
        for rec in self:
            # Get actual equipment allocation costs
            allocated_cost = sum(rec.equipment_allocation_ids.mapped('total_cost'))
            if allocated_cost:
                rec.equipment_cost = allocated_cost
            else:
                # Fallback to BOQ equipment costs
                equipment_boq = rec.boq_ids.filtered(
                    lambda x: 'equipment' in x.name.lower() or 'tool' in x.name.lower())
                rec.equipment_cost = sum(equipment_boq.mapped('total_price'))