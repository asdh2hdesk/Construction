# File: models/account_payment.py
from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    construction_project_id = fields.Many2one(
        'construction.project',
        string='Construction Project'
    )
    payment_type_construction = fields.Selection([
        ('advance', 'Advance Payment'),
        ('progress', 'Progress Payment'),
        ('retention', 'Retention Release'),
        ('final', 'Final Payment')
    ], string='Construction Payment Type')