# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval


class ProjectIssue(models.Model):
    _name = "project.issue"
    _inherit = ['project.issue', 'rating.mixin']

    @api.multi
    def write(self, values):
        res = super(ProjectIssue, self).write(values)
        if 'stage_id' in values and values.get('stage_id'):
            self.filtered(lambda x: x.project_id.rating_status == 'stage')._send_issue_rating_mail(force_send=True)
        return res

    def _send_issue_rating_mail(self, force_send=False):
        for issue in self:
            rating_template = issue.stage_id.rating_template_id
            if rating_template:
                issue.rating_send_request(rating_template, lang=issue.partner_id.lang, force_send=force_send)

    @api.multi
    def rating_apply(self, rate, token=None, feedback=None, subtype=None):
        return super(ProjectIssue, self).rating_apply(rate, token=token, feedback=feedback, subtype="rating_project_issue.mt_issue_rating")

    def rating_get_parent_model_name(self, vals):
        return 'project.project'

    def rating_get_parent_id(self):
        return self.project_id.id


class Stage(models.Model):

    _inherit = 'project.task.type'

    def _default_domain_rating_template_id(self):
        domain = super(Stage, self)._default_domain_rating_template_id()
        return ['|'] + domain + [('model', '=', 'project.issue')]


class Project(models.Model):

    _inherit = "project.project"

    def _send_rating_mail(self):
        super(Project, self)._send_rating_mail()
        for project in self:
            self.env['project.issue'].search([('project_id', '=', project.id)])._send_issue_rating_mail()

    @api.depends('percentage_satisfaction_task', 'percentage_satisfaction_issue')
    def _compute_percentage_satisfaction_project(self):
        super(Project, self)._compute_percentage_satisfaction_project()
        for project in self:
            domain = [('create_date', '>=', fields.Datetime.to_string(fields.datetime.now() - timedelta(days=30)))]
            activity_great, activity_sum = 0, 0
            if project.use_tasks:
                activity_task = project.tasks.rating_get_grades(domain)
                activity_great = activity_task['great']
                activity_sum = sum(pycompat.values(activity_task))
            if project.use_issues:
                activity_issue = self.env['project.issue'].search([('project_id', '=', project.id)]).rating_get_grades(domain)
                activity_great += activity_issue['great']
                activity_sum += sum(pycompat.values(activity_issue))
            project.percentage_satisfaction_project = activity_great * 100 / activity_sum if activity_sum else -1

    @api.one
    @api.depends('issue_ids.rating_ids.rating')
    def _compute_percentage_satisfaction_issue(self):
        project_issue = self.env['project.issue'].search([('project_id', '=', self.id)])
        activity = project_issue.rating_get_grades()
        self.percentage_satisfaction_issue = activity['great'] * 100 / sum(pycompat.values(activity)) if sum(pycompat.values(activity)) else -1

    percentage_satisfaction_issue = fields.Integer(compute='_compute_percentage_satisfaction_issue', string="Happy % on Issue", store=True, default=-1)

    @api.multi
    def action_view_all_rating(self):
        action = super(Project, self).action_view_all_rating()
        if self.use_issues:  # add default filter for issue rating
            action['context']['search_default_rating_issues'] = 1
        return action
