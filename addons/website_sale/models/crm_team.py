# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _


class CrmTeam(models.Model):
    _inherit = "crm.team"

    website_ids = fields.One2many('website', 'salesteam_id', string='Websites', help="Websites using this sales channel")
    abandoned_carts_count = fields.Integer(
        compute='_compute_abandoned_carts',
        string='Number of Abandoned Carts', readonly=True)
    abandoned_carts_amount = fields.Integer(
        compute='_compute_abandoned_carts',
        string='Amount of Abandoned Carts', readonly=True)

    def _compute_abandoned_carts(self):
        # abandoned carts are draft sales orders that have no order lines,
        # a partner other than the public user, and created over an hour ago
        website_teams = self.filtered(lambda team: team.team_type == 'website')
        if website_teams:
            abandoned_carts_data = self.env['sale.order'].read_group([
                ('team_id', 'in', website_teams.ids),
                ('date_order', '<', fields.Datetime.to_string(datetime.now() - relativedelta(hours=1))),
                ('state', '=', 'draft'),
                ('partner_id', '!=', self.env.ref('base.public_partner').id),
                ('order_line', '!=', False),
            ], ['amount_total', 'team_id'], ['team_id'])
            counts = {data['team_id'][0]: data['team_id_count'] for data in abandoned_carts_data}
            amounts = {data['team_id'][0]: data['amount_total'] for data in abandoned_carts_data}
            for team in website_teams:
                team.abandoned_carts_count = counts.get(team.id, 0)
                team.abandoned_carts_amount = amounts.get(team.id, 0)

    def _compute_dashboard_button_name(self):
        website_teams = self.filtered(lambda team: team.team_type == 'website' and not team.use_quotations)
        website_teams.update({'dashboard_button_name': _("Online Sales")})
        super(CrmTeam, self - website_teams)._compute_dashboard_button_name()

    def get_abandoned_carts(self):
        self.ensure_one()
        time_constraint = fields.Datetime.to_string(fields.datetime.now() - relativedelta(hours=1))
        return {
            'name': _('Abandoned Carts'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'draft'), ('partner_id', '!=', self.env.ref('base.public_partner').id), ('date_order', '<', time_constraint)],
            'search_view_id': self.env.ref('sale.sale_order_view_search_inherit_sale').id,
            'context': {'search_default_team_id': self.id, 'default_team_id': self.id},
            'res_model': 'sale.order',
            'help': _('''<p class="oe_view_nocontent_create">
                        You can find all abandoned carts here, i.e. the carts generated by your website's visitors from over an hour ago that haven't been confirmed yet.</p>
                        <p>You should send an email to the customers to encourage them!</p>
                    '''),
        }
