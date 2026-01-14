from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class ConstructionProject(models.Model):
    _name = 'construction.project'
    _description = 'Construction Project'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'translation.mixin']

    name = fields.Char(string='Project Name', required=True, tracking=True)
    contract_value = fields.Monetary(string='Contract Value', tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    material_cost = fields.Monetary(string='Material Cost', compute='_compute_material_cost', store=True)
    labor_cost = fields.Monetary(string='Labor Cost', compute='_compute_labor_cost', store=True)
    equipment_cost = fields.Monetary(string='Equipment Cost', compute='_compute_equipment_cost', store=True)
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost', store=True)

    progress_percent = fields.Float(string='Progress %', compute='_compute_progress', store=True)

    purchase_ids = fields.One2many('purchase.order', 'construction_project_id', string='Purchases')
    timesheet_ids = fields.One2many('account.analytic.line', 'construction_project_id', string='Timesheets')
    stock_move_ids = fields.One2many('stock.move', 'construction_project_id', string='Inventory Moves')
    invoice_ids = fields.One2many('account.move', 'construction_project_id', string='Invoices')
    payment_ids = fields.One2many('account.payment', 'construction_project_id', string='Payments')

    start_date = fields.Date(string='Actual Start Date')
    end_date = fields.Date(string='Actual Completion Date')
    e_start_date = fields.Date(string='Expected Start Date')
    e_end_date = fields.Date(string='Expected Completion Date')

    e_contract_value = fields.Monetary(string='Expected Contract Value', tracking=True)
    # currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    e_material_cost = fields.Monetary(string='Expected Material Cost', store=True)
    e_labor_cost = fields.Monetary(string='Expected Labor Cost', store=True)
    e_equipment_cost = fields.Monetary(string='Expected Equipment Cost', store=True)
    e_total_cost = fields.Monetary(string='Expected Total Cost', compute='_compute_e_total_cost', store=True)

    # asset_ids = fields.One2many('account.asset', 'construction_project_id', string='Assets')

    # Basic project info
    # start_date = fields.Date(string='Start Date')
    # end_date = fields.Date(string='End Date')
    description = fields.Text(string='Description')
    partner_id = fields.Many2one('res.partner', string='Customer')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')

    # Related records - basic ones only
    boq_ids = fields.One2many('construction.boq', 'project_id', string='BOQ Items')
    progress_ids = fields.One2many('construction.progress', 'project_id', string='Progress Updates')
    dpr_ids = fields.One2many('construction.dpr', 'project_id', string='Daily Reports')
    quality_ids = fields.One2many('construction.quality', 'project_id', string='Quality Records')

    timeline_ids = fields.One2many('project.task.simple', 'project_id', string='Project Timeline')

    def action_view_timeline(self):
        """Open timeline view for this project"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Timeline',
            'res_model': 'project.task.simple',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id, 'default_start_date': self.start_date or fields.Date.today(),
                        'search_default_project_id': self.id}
        }

    @api.depends('timeline_ids.progress_percent', 'timeline_ids.parent_id')
    def _compute_progress(self):
        for project in self:
            # Only consider main tasks (not subtasks) for project progress
            main_tasks = project.timeline_ids.filtered(lambda t: not t.parent_id)
            if main_tasks:
                total_progress = sum(main_tasks.mapped('progress_percent'))
                count = len(main_tasks)
                project.progress_percent = total_progress / count if count > 0 else 0.0
            else:
                project.progress_percent = 0.0

    def action_view_timeline_hierarchy(self):
        """Open hierarchical timeline view for this project"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Timeline',
            'res_model': 'project.task.simple',
            'view_mode': 'tree,gantt,form',
            'views': [
                (self.env.ref('your_module.view_project_task_simple_tree').id, 'tree'),
                (self.env.ref('your_module.view_project_task_simple_gantt').id, 'gantt'),
                (False, 'form')
            ],
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'default_start_date': self.start_date or fields.Date.today(),
                'search_default_project_id': self.id,
                'expand': 1,  # Expand tree view by default
            }
        }

    def create_sample_timeline_with_subtasks(self):
        """Helper method to create sample timeline structure with subtasks"""
        # Create main task: Cabin 36 sq ft
        cabin_task = self.env['project.task.simple'].create({
            'name': 'Cabin 36 sq ft',
            'project_id': self.id,
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today() + timedelta(days=8),
            'progress_percent': 50.0,
            'status': 'in_progress'
        })

        # Create subtasks for cabin
        cabin_subtasks = [
            {'name': 'Foundation', 'days': 2, 'progress': 100, 'status': 'completed'},
            {'name': 'Framing', 'days': 3, 'progress': 80, 'status': 'in_progress'},
            {'name': 'Roofing', 'days': 2, 'progress': 20, 'status': 'not_started'},
            {'name': 'Finishing', 'days': 1, 'progress': 0, 'status': 'not_started'},
        ]

        start_date = cabin_task.start_date
        for subtask in cabin_subtasks:
            self.env['project.task.simple'].create({
                'name': subtask['name'],
                'parent_id': cabin_task.id,
                'project_id': self.id,
                'start_date': start_date,
                'end_date': start_date + timedelta(days=subtask['days'] - 1),
                'progress_percent': subtask['progress'],
                'status': subtask['status']
            })
            start_date += timedelta(days=subtask['days'])

        # Create main task: Conference Room
        conf_task = self.env['project.task.simple'].create({
            'name': 'Conference Room',
            'project_id': self.id,
            'start_date': fields.Date.today() + timedelta(days=5),
            'end_date': fields.Date.today() + timedelta(days=11),
            'progress_percent': 30.0,
            'status': 'in_progress'
        })

        # Create subtasks for conference room
        conf_subtasks = [
            {'name': 'Space Planning', 'days': 1, 'progress': 100, 'status': 'completed'},
            {'name': 'Electrical Setup', 'days': 2, 'progress': 50, 'status': 'in_progress'},
            {'name': 'Flooring', 'days': 2, 'progress': 0, 'status': 'not_started'},
            {'name': 'Furniture Installation', 'days': 1, 'progress': 0, 'status': 'not_started'},
        ]

        start_date = conf_task.start_date
        for subtask in conf_subtasks:
            self.env['project.task.simple'].create({
                'name': subtask['name'],
                'parent_id': conf_task.id,
                'project_id': self.id,
                'start_date': start_date,
                'end_date': start_date + timedelta(days=subtask['days'] - 1),
                'progress_percent': subtask['progress'],
                'status': subtask['status']
            })
            start_date += timedelta(days=subtask['days'])

    @api.depends('boq_ids.total_price', 'purchase_ids.amount_total')
    def _compute_material_cost(self):
        for rec in self:
            # Use actual purchase costs if available, otherwise BOQ estimates
            purchase_cost = sum(
                rec.purchase_ids.filtered(lambda x: x.state in ['purchase', 'done']).mapped('amount_total'))
            boq_cost = sum(rec.boq_ids.filtered(lambda x: not x.parent_id).mapped('total_price'))
            rec.material_cost = purchase_cost if purchase_cost else boq_cost

    @api.depends('dpr_ids.employee_count', 'dpr_ids.working_hours', 'dpr_ids.per_cost')
    def _compute_labor_cost(self):
        for rec in self:
            total = 0.0
            for dpr in rec.dpr_ids:
                # per_cost is per day per employee, multiply with working hours and employee count
                total += dpr.per_cost * dpr.working_hours * dpr.employee_count
            rec.labor_cost = total

    @api.depends('boq_ids.total_price')  # Simple equipment cost from BOQ
    def _compute_equipment_cost(self):
        for rec in self:
            # Simple approach: get equipment costs from BOQ items marked as equipment
            equipment_boq = rec.boq_ids.filtered(lambda x: 'equipment' in x.name.lower() or 'tool' in x.name.lower())
            rec.equipment_cost = sum(equipment_boq.mapped('total_price'))

    # Financial computed fields
    total_invoiced = fields.Monetary(string='Total Invoiced', compute='_compute_total_invoiced', store=True)
    total_paid = fields.Monetary(string='Total Paid', compute='_compute_total_paid', store=True)

    @api.depends('material_cost', 'labor_cost', 'equipment_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = (rec.material_cost or 0.0) + (rec.labor_cost or 0.0) + (rec.equipment_cost or 0.0) + (rec.contract_value or 0.0)

    @api.depends('e_material_cost', 'e_labor_cost', 'e_equipment_cost')
    def _compute_e_total_cost(self):
        for rec in self:
            rec.e_total_cost = (rec.e_material_cost or 0.0) + (rec.e_labor_cost or 0.0) + (rec.e_equipment_cost or 0.0) + (rec.e_contract_value or 0.0)

    @api.depends('invoice_ids.amount_total')
    def _compute_total_invoiced(self):
        for rec in self:
            rec.total_invoiced = sum(rec.invoice_ids.filtered(lambda x: x.state == 'posted').mapped('amount_total'))

    @api.depends('payment_ids.amount')
    def _compute_total_paid(self):
        for rec in self:
            rec.total_paid = sum(rec.payment_ids.filtered(lambda x: x.state == 'posted').mapped('amount'))

    # Progress billing method
    def create_progress_invoice(self, billing_percentage):
        """Create invoice based on project progress"""
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'construction_project_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': f'Progress Billing - {self.name} ({billing_percentage}%)',
                'quantity': 1,
                'price_unit': self.contract_value * (billing_percentage / 100),
            })]
        }
        return self.env['account.move'].create(invoice_vals)

    def action_open_project_dashboard(self):
        """Open individual project dashboard"""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "construction_project_dashboard.client_action",
            "name": f"{self.name} - Dashboard",
            "context": {
                "project_id": self.id,
                "project_name": self.name,
                "active_id": self.id,
                "active_ids": [self.id],
                "active_model": "construction.project",
            },
            "target": "current",
        }


class ProjectTask(models.Model):
    _name = 'project.task.simple'
    _description = 'Project Timeline Task'
    _order = 'sequence, start_date'
    _parent_store = True
    _inherit = ['mail.thread', 'mail.activity.mixin', 'translation.mixin']

    name = fields.Char(string='Task Name', translate=True)
    project_id = fields.Many2one('construction.project', string='Project',
                                 domain="[('state', '!=', 'cancelled')]")
    sequence = fields.Integer(string='Order', default=10)

    # Hierarchical fields for parent-child relationships
    parent_id = fields.Many2one('project.task.simple', string='Parent Task', ondelete='cascade')
    child_ids = fields.One2many('project.task.simple', 'parent_id', string='Subtasks')
    parent_path = fields.Char(index=True)

    # Display name with indentation for hierarchy
    display_name = fields.Char(store=True, translate=True)
    level = fields.Integer(compute='_compute_level', store=True, string='Level')

    # Task type to differentiate main tasks from subtasks
    is_subtask = fields.Boolean(compute='_compute_is_subtask', store=True)

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    duration = fields.Integer(string='Days', compute='_compute_duration', store=True)
    progress_percent = fields.Float(
        string='Progress %',
        compute='_compute_progress_percent',
        store=True,
        readonly=False  # keep editable for leaf tasks (no children)
    )
    description = fields.Text(string='Description', translate=True)
    assigned_to = fields.Many2one('res.users', string='Assigned To')

    status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='not_started')

    @api.depends('child_ids.progress_percent')
    def _compute_progress_percent(self):
        """Compute progress: parent = avg of children, leaf = keep own value"""
        for task in self:
            if task.child_ids:
                total_progress = sum(task.child_ids.mapped('progress_percent'))
                count = len(task.child_ids)
                task.progress_percent = total_progress / count if count > 0 else 0.0
            else:
                # For leaf tasks, keep existing value (default/manual entry)
                if not task.progress_percent:
                    task.progress_percent = 0.0

    @api.depends('parent_id')
    def _compute_is_subtask(self):
        for task in self:
            task.is_subtask = bool(task.parent_id)

    @api.depends('parent_path')
    def _compute_level(self):
        for task in self:
            task.level = len(task.parent_path.split('/')) - 2 if task.parent_path else 0

    # @api.depends('name', 'level')
    # def _compute_display_name(self):
    #     for task in self:
    #         indent = '    ' * task.level  # 4 spaces per level
    #         task.display_name = f"{indent}{task.name}"

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for task in self:
            if task.start_date and task.end_date:
                delta = task.end_date - task.start_date
                task.duration = delta.days + 1
            else:
                task.duration = 0
    #
    # @api.depends('child_ids.progress_percent')
    # def _compute_parent_progress(self):
    #     """Compute parent task progress based on child tasks"""
    #     for task in self:
    #         if task.child_ids:
    #             total_progress = sum(task.child_ids.mapped('progress_percent'))
    #             count = len(task.child_ids)
    #             task.progress_percent = total_progress / count if count > 0 else 0.0

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        """Auto-set project_id from parent when parent is selected"""
        if self.parent_id:
            self.project_id = self.parent_id.project_id

    @api.onchange('child_ids')
    def _onchange_child_ids(self):
        if self.child_ids:
            self.update({'progress_percent': self.progress_percent})

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """Prevent circular references in parent-child relationships"""
        if not self._check_recursion():
            raise ValidationError('You cannot create recursive task hierarchies.')

    def action_add_subtask(self):
        """Action to add a subtask to current task"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Subtask',
            'res_model': 'project.task.simple',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_parent_id': self.id,
                'default_project_id': self.project_id.id,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
            }
        }

    def action_view_subtasks(self):
        """Action to view all subtasks of current task"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Subtasks of {self.name}',
            'res_model': 'project.task.simple',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_project_id': self.project_id.id,
            }
        }