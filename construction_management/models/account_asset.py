from odoo import models, fields


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    construction_project_id = fields.Many2one(
        'construction.project',
        string='Construction Project'
    )
    asset_type = fields.Selection([
        ('equipment', 'Equipment'),
        ('tool', 'Tools'),
        ('vehicle', 'Vehicle'),
        ('temporary', 'Temporary Structure')
    ], string='Asset Type')