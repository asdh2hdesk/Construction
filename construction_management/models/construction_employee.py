from odoo import models, fields, api
from datetime import datetime, timedelta


class ConstructionEmployeeWork(models.Model):
    _name = 'construction.employee.work'
    _description = 'Construction Employee Work Records'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'work_date desc, employee_id'

    name = fields.Char(string='Reference', required=True, default='New', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    project_id = fields.Many2one('construction.project', string='Project', required=True, tracking=True)
    work_date = fields.Date(string='Work Date', required=True, default=fields.Date.context_today, tracking=True)
    construction_task_id = fields.Many2one(
        'project.task.simple',
        string='Task', domain="[('project_id', '=', project_id)]"
    )
    # Working hours
    start_time = fields.Float(string='Start Time', help='Start time in 24-hour format (e.g., 8.5 for 8:30 AM)')
    end_time = fields.Float(string='End Time', help='End time in 24-hour format (e.g., 17.5 for 5:30 PM)')
    break_hours = fields.Float(string='Break Hours', default=1.0, help='Total break time in hours')
    working_hours = fields.Float(string='Working Hours', compute='_compute_working_hours', store=True)
    overtime_hours = fields.Float(string='Overtime Hours', compute='_compute_overtime_hours', store=True)

    # Task details
    task_description = fields.Text(string='Task Description', tracking=True, translate=True)
    # task_category = fields.Selection([
    # ], string='Task Category', required=True)

    # Payment information
    hourly_rate = fields.Monetary(string='Hourly Rate', required=True, tracking=True)
    overtime_rate = fields.Monetary(string='Overtime Rate', compute='_compute_overtime_rate', store=True)
    regular_pay = fields.Monetary(string='Regular Pay', compute='_compute_regular_pay', store=True)
    overtime_pay = fields.Monetary(string='Overtime Pay', compute='_compute_overtime_pay', store=True)
    total_pay = fields.Monetary(string='Total Pay', compute='_compute_total_pay', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Payment status
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid')
    ], string='Payment Status', default='pending', tracking=True)

    paid_amount = fields.Monetary(string='Paid Amount', tracking=True)
    payment_date = fields.Date(string='Payment Date')
    payment_reference = fields.Char(string='Payment Reference')

    # Additional fields
    location = fields.Char(string='Work Location')
    notes = fields.Text(string='Notes', translate=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Approval fields
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor')
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('construction.employee.work') or 'New'
        return super().create(vals)

    @api.depends('start_time', 'end_time', 'break_hours')
    def _compute_working_hours(self):
        for record in self:
            if record.start_time and record.end_time:
                total_time = record.end_time - record.start_time
                record.working_hours = max(0, total_time - (record.break_hours or 0))
            else:
                record.working_hours = 0.0

    @api.depends('working_hours')
    def _compute_overtime_hours(self):
        for record in self:
            # Standard working day is 8 hours
            standard_hours = 8.0
            record.overtime_hours = max(0, record.working_hours - standard_hours)

    @api.depends('hourly_rate')
    def _compute_overtime_rate(self):
        for record in self:
            # Overtime rate is typically 1.5x regular rate
            record.overtime_rate = record.hourly_rate * 1.5

    @api.depends('working_hours', 'overtime_hours', 'hourly_rate')
    def _compute_regular_pay(self):
        for record in self:
            regular_hours = record.working_hours - record.overtime_hours
            record.regular_pay = regular_hours * record.hourly_rate

    @api.depends('overtime_hours', 'overtime_rate')
    def _compute_overtime_pay(self):
        for record in self:
            record.overtime_pay = record.overtime_hours * record.overtime_rate

    @api.depends('regular_pay', 'overtime_pay')
    def _compute_total_pay(self):
        for record in self:
            record.total_pay = record.regular_pay + record.overtime_pay

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            # You can set default hourly rate from employee contract or job position
            # This is a simplified approach
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            if contract and contract.wage:
                # Assuming monthly wage, convert to hourly (assuming 8 hours/day, 22 working days/month)
                self.hourly_rate = contract.wage / (8 * 22)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset_to_draft(self):
        self.state = 'draft'

    def action_mark_paid(self):
        self.write({
            'payment_status': 'paid',
            'paid_amount': self.total_pay,
            'payment_date': fields.Date.context_today(self)
        })


class ConstructionProject(models.Model):
    _inherit = 'construction.project'

    # Add employee work records to project
    employee_work_ids = fields.One2many('construction.employee.work', 'project_id',
                                        string='Employee Work Records')
    total_labor_cost_from_work = fields.Monetary(string='Labor Cost (Work Records)',
                                                 compute='_compute_labor_cost_from_work', store=True)

    @api.depends('employee_work_ids.total_pay')
    def _compute_labor_cost_from_work(self):
        for project in self:
            project.total_labor_cost_from_work = sum(
                project.employee_work_ids.filtered(lambda x: x.state == 'approved').mapped('total_pay')
            )


# Add sequence for employee work records
class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def _get_construction_employee_work_sequence(self):
        sequence = self.env['ir.sequence'].search([('code', '=', 'construction.employee.work')], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].create({
                'name': 'Construction Employee Work',
                'code': 'construction.employee.work',
                'prefix': 'EW',
                'padding': 4,
                'number_increment': 1,
            })
        return sequence