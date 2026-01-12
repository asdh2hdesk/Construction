from odoo import models, fields, api

class ConstructionProgress(models.Model):
    _name = 'construction.progress'
    _description = 'Construction Progress'

    name = fields.Char(string='Progress Entry', translate=True)
    project_id = fields.Many2one('construction.project', string='Project', required=True)
    task_id = fields.Many2one('project.task', string='Task')
    date = fields.Date(string='Date', default=fields.Date.today)
    progress_percent = fields.Float(string='Progress %', required=True)
    description = fields.Text(string='Notes', translate=True)

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # Optional: Update project overall progress
        project = rec.project_id
        total = sum(project.progress_ids.mapped('progress_percent'))
        count = len(project.progress_ids)
        if count:
            project.progress_percent = total / count
        return rec

# class ConstructionProject(models.Model):
#     _inherit = 'construction.project'
#
#     progress_ids = fields.One2many('construction.progress', 'project_id', string='Progress Updates')
