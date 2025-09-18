from odoo import models, fields, api, tools


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    construction_project_id = fields.Many2one(
        'construction.project',
        string='Project'
    )
    construction_task_id = fields.Many2one(
        'project.task.simple',
        string='Task', domain="[('project_id', '=', construction_project_id)]"
    )

    boq_item_id = fields.Many2one(
        'construction.boq',
        string='BOQ Item'
    )
    image_attachment = fields.Binary(
        string='Image Attachment',
        help='Attach an image related to this timesheet entry'
    )

    image_filename = fields.Char(string='Image Filename')
