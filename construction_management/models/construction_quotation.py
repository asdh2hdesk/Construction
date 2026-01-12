# File: models/construction_quotation.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ConstructionQuotation(models.Model):
    _name = 'construction.quotation'
    _description = 'Construction Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_quotation desc'

    name = fields.Char(string='Quotation Number', required=True, copy=False,
                       readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Client', required=True,
                                 tracking=True)
    date_quotation = fields.Date(string='Quotation Date', default=fields.Date.today,
                                 required=True, tracking=True)
    validity_date = fields.Date(string='Valid Until', tracking=True)

    # Link to CRM opportunity
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity',
                                     tracking=True,
                                     domain="[('type', '=', 'opportunity')]")

    # Link to project (when quotation is converted)
    project_id = fields.Many2one('construction.project', string='Project',
                                 readonly=True, tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Quotation lines
    line_ids = fields.One2many('construction.quotation.line', 'quotation_id',
                               string='Quotation Lines')

    # Computed totals
    material_total = fields.Monetary(string='Material Total',
                                     compute='_compute_totals', store=True)
    labor_total = fields.Monetary(string='Labor Total',
                                  compute='_compute_totals', store=True)
    equipment_total = fields.Monetary(string='Equipment Total',
                                      compute='_compute_totals', store=True)
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_totals',
                               store=True)

    # Additional costs
    transport_cost = fields.Monetary(string='Transport Cost', default=0.0)
    margin_percent = fields.Float(string='Margin (%)', default=15.0)
    margin_amount = fields.Monetary(string='Margin Amount',
                                    compute='_compute_totals', store=True)
    vat_percent = fields.Float(string='VAT (%)', default=18.0)
    vat_amount = fields.Monetary(string='VAT Amount',
                                 compute='_compute_totals', store=True)
    total_amount = fields.Monetary(string='Total Amount',
                                   compute='_compute_totals', store=True)

    contract_value = fields.Monetary(
        string='Contract Value',
        tracking=True,
        help='Final agreed contract value with the client (can be different from calculated total)'
    )

    notes = fields.Text(string='Terms & Conditions' ,translate=True)
    internal_notes = fields.Text(string='Internal Notes' ,translate=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted to Project')
    ], string='Status', default='draft', tracking=True)


    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('construction.quotation') or 'New'
        return super(ConstructionQuotation, self).create(vals)

    @api.depends('line_ids.material_cost', 'line_ids.labor_cost',
                 'line_ids.equipment_cost', 'transport_cost', 'margin_percent',
                 'vat_percent')
    def _compute_totals(self):
        for quotation in self:
            quotation.material_total = sum(quotation.line_ids.mapped('material_cost'))
            quotation.labor_total = sum(quotation.line_ids.mapped('labor_cost'))
            quotation.equipment_total = sum(quotation.line_ids.mapped('equipment_cost'))

            quotation.subtotal = (quotation.material_total +
                                  quotation.labor_total +
                                  quotation.equipment_total +
                                  quotation.transport_cost)

            quotation.margin_amount = quotation.subtotal * (quotation.margin_percent / 100)

            subtotal_with_margin = quotation.subtotal + quotation.margin_amount
            quotation.vat_amount = subtotal_with_margin * (quotation.vat_percent / 100)

            quotation.total_amount = subtotal_with_margin + quotation.vat_amount

    def action_send_quotation(self):
        """Send quotation to client"""
        self.ensure_one()
        self.state = 'sent'
        # Update opportunity stage if linked
        if self.opportunity_id:
            self.opportunity_id.write({'stage_id': self.env.ref('crm.stage_lead2').id})
        return True

    def action_approve(self):
        """Approve quotation"""
        self.ensure_one()
        self.state = 'approved'
        return True

    def action_reject(self):
        """Reject quotation"""
        self.ensure_one()
        self.state = 'rejected'
        if self.opportunity_id:
            self.opportunity_id.action_set_lost()
        return True

    def action_convert_to_project(self):
        """Convert approved quotation to construction project"""
        self.ensure_one()

        if self.project_id:
            return self.action_view_project()

        # NOW check if state is approved (only for new conversions)
        if self.state != 'approved':
            raise ValidationError(f'Only approved quotations can be converted to projects. Current state: {self.state}')

        # Use manual contract_value if set, otherwise fall back to total_amount
        project_contract_value = self.contract_value or self.total_amount

        # Create project
        project = self.env['construction.project'].create({
            'name': self.name + ' - Project',
            'partner_id': self.partner_id.id,
            # 'contract_value': project_contract_value,
            'e_contract_value': project_contract_value,
            'e_material_cost': self.material_total,
            'e_labor_cost': self.labor_total,
            'e_equipment_cost': self.equipment_total,
            'description': self.notes or '',
            'state': 'active',
        })

        _logger.info(f"Created project {project.name} (ID: {project.id})")

        # Create BOQ items from quotation lines
        for idx, line in enumerate(self.line_ids, start=1):
            self.env['construction.boq'].create({
                'project_id': project.id,
                'name': f'BOQ-{project.id}-{idx:03d}',
                'quantity': line.quantity,
                'unit': line.unit,
                'unit_price': line.material_cost / line.quantity if line.quantity else 0,
                'total_price': line.material_cost,
            })

        # Link quotation to project
        self.write({
            'project_id': project.id,
            'state': 'converted'
        })

        # Mark opportunity as won if linked
        if self.opportunity_id:
            self.opportunity_id.action_set_won()

        return self.action_view_project()

    def action_view_project(self):
        """View the linked project"""
        self.ensure_one()

        if not self.project_id:
            raise ValidationError('No project linked to this quotation.')


        return {
            'type': 'ir.actions.act_window',
            'name': 'Construction Project',
            'res_model': 'construction.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_quotation(self):
        """Print quotation as PDF"""
        self.ensure_one()
        return self.env.ref('construction_management.action_report_construction_quotation').report_action(self)


class ConstructionQuotationLine(models.Model):
    _name = 'construction.quotation.line'
    _description = 'Construction Quotation Line'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('construction.quotation', string='Quotation',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    # Work type selection
    work_type = fields.Selection([
        ('ceiling_plaster', 'Ceiling Plaster (Staff)'),
        ('partition', 'Partitions'),
        ('painting', 'Painting'),
        ('tiling', 'Tiling'),
        ('flooring', 'Flooring'),
        ('electrical', 'Electrical Work'),
        ('plumbing', 'Plumbing'),
        ('carpentry', 'Carpentry'),
        ('masonry', 'Masonry'),
        ('roofing', 'Roofing'),
        ('other', 'Other')
    ], string='Work Type', required=True)

    description = fields.Text(string='Description')

    # Input parameters
    surface_area = fields.Float(string='Surface (m²)', default=0.0)
    length = fields.Float(string='Length (m)', default=0.0)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    unit = fields.Selection([
        ('m2', 'm²'),
        ('m', 'm'),
        ('unit', 'Unit'),
        ('kg', 'kg'),
        ('ton', 'Ton'),
        ('bag', 'Bag'),
        ('piece', 'Piece')
    ], string='Unit', default='m2', required=True)

    finishing_type = fields.Char(string='Finishing Type' ,translate=True)
    waste_percent = fields.Float(string='Waste %', default=5.0)

    # Costs
    material_unit_cost = fields.Monetary(string='Material Unit Cost',
                                         currency_field='currency_id')
    material_cost = fields.Monetary(string='Material Cost',
                                    compute='_compute_costs', store=True,
                                    currency_field='currency_id')

    labor_days = fields.Float(string='Labor Days', default=1.0)
    labor_rate_per_day = fields.Monetary(string='Labor Rate/Day',
                                         currency_field='currency_id')
    labor_cost = fields.Monetary(string='Labor Cost',
                                 compute='_compute_costs', store=True,
                                 currency_field='currency_id')

    equipment_cost = fields.Monetary(string='Equipment Cost', default=0.0,
                                     currency_field='currency_id')

    line_total = fields.Monetary(string='Line Total',
                                 compute='_compute_costs', store=True,
                                 currency_field='currency_id')

    currency_id = fields.Many2one('res.currency',
                                  related='quotation_id.currency_id',
                                  store=True, readonly=True)

    @api.depends('surface_area', 'quantity', 'material_unit_cost', 'waste_percent',
                 'labor_days', 'labor_rate_per_day', 'equipment_cost')
    def _compute_costs(self):
        for line in self:
            # Use surface_area if available, otherwise use quantity
            base_qty = line.surface_area if line.surface_area > 0 else line.quantity

            # Material cost with waste
            qty_with_waste = base_qty * (1 + line.waste_percent / 100)
            line.material_cost = qty_with_waste * line.material_unit_cost

            # Labor cost
            line.labor_cost = line.labor_days * line.labor_rate_per_day

            # Total line cost
            line.line_total = line.material_cost + line.labor_cost + line.equipment_cost

    @api.onchange('work_type')
    def _onchange_work_type(self):
        """Set default values based on work type"""
        if self.work_type == 'ceiling_plaster':
            self.unit = 'm2'
            self.labor_days = 0.5
            self.waste_percent = 10.0
        elif self.work_type == 'painting':
            self.unit = 'm2'
            self.labor_days = 0.3
            self.waste_percent = 5.0
        elif self.work_type == 'tiling':
            self.unit = 'm2'
            self.labor_days = 0.8
            self.waste_percent = 10.0
        elif self.work_type == 'partition':
            self.unit = 'm2'
            self.labor_days = 1.0
            self.waste_percent = 5.0


# File: models/crm_lead.py
from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    quotation_ids = fields.One2many('construction.quotation', 'opportunity_id',
                                    string='Quotations')
    quotation_count = fields.Integer(string='Quotation Count',
                                     compute='_compute_quotation_count')

    project_ids = fields.One2many('construction.project', 'partner_id',
                                  string='Projects',
                                  domain="[('partner_id', '=', partner_id)]")
    project_count = fields.Integer(string='Project Count',
                                   compute='_compute_project_count')

    @api.depends('quotation_ids')
    def _compute_quotation_count(self):
        for lead in self:
            lead.quotation_count = len(lead.quotation_ids)

    @api.depends('project_ids')
    def _compute_project_count(self):
        for lead in self:
            lead.project_count = len(lead.project_ids)

    def action_create_quotation(self):
        """Create new quotation from opportunity"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Quotation',
            'res_model': 'construction.quotation',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_opportunity_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_view_quotations(self):
        """View all quotations for this opportunity"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotations',
            'res_model': 'construction.quotation',
            'view_mode': 'tree,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {'default_opportunity_id': self.id}
        }

    def action_view_projects(self):
        """View all projects for this customer"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Projects',
            'res_model': 'construction.project',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
        }