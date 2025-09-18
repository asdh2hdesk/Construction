from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    construction_project_id = fields.Many2one(
        'construction.project',
        string='Construction Project'
    )
    boq_item_id = fields.Many2one(
        'construction.boq',
        string='BOQ Item'
    )
    dpr_material_id = fields.Many2one(
        'construction.dpr.material',
        string='DPR Material Entry'
    )