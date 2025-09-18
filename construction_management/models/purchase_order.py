from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    construction_project_id = fields.Many2one(
        'construction.project',
        string='Construction Project',
        help="Link this purchase to a construction project"
    )
    boq_item_id = fields.Many2one(
        'construction.boq',
        string='BOQ Item',
        help="Link to specific BOQ item being purchased"
    )