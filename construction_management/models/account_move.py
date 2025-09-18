# File: models/account_move.py
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    construction_project_id = fields.Many2one(
        'construction.project',
        string='Construction Project'
    )
    progress_billing = fields.Boolean(
        string='Progress Billing',
        help="Invoice based on project completion percentage"
    )
    billing_percentage = fields.Float(
        string='Billing %',
        help="Percentage of project being billed"
    )