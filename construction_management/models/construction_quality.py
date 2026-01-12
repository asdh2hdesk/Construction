from odoo import models, fields

class ConstructionQuality(models.Model):
    _name = 'construction.quality'
    _description = 'Quality & Safety'

    project_id = fields.Many2one('construction.project', string='Project')
    inspection_date = fields.Date(string='Inspection Date')
    checklist = fields.Text(string='Checklist', translate=True)
    issues_found = fields.Text(string='Issues Found', translate=True)
    corrective_actions = fields.Text(string='Corrective Actions', translate=True)
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'construction.quality')],
        string='Image Attachments'
    )

    image_filename = fields.Char(string='Image Filename')
