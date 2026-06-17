# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KioCapacityDashboard(models.Model):
    _name = "kio.capacity.dashboard"
    _description = "KIO Capacity Dashboard"

    name = fields.Char(default="Capacity Overview", required=True)

    total_capacity = fields.Float(
        string="Total Capacity",
        compute="_compute_realtime_capacity",
        store=False,
    )

    bandwidth_capacity = fields.Float(
        string="Bandwidth Capacity",
        compute="_compute_realtime_capacity",
        store=False,
    )

    mac_capacity = fields.Float(
        string="MAC Capacity",
        compute="_compute_realtime_capacity",
        store=False,
    )

    free_capacity = fields.Float(
        string="Free Capacity",
        compute="_compute_realtime_capacity",
        store=False,
    )

    upgrade_capacity = fields.Float(
        string="Upgrade Capacity",
        default=0.0,
    )

    downgrade_capacity = fields.Float(
        string="Downgrade Capacity",
        default=0.0,
    )

    customer_line_ids = fields.One2many(
        "kio.capacity.dashboard.customer",
        "dashboard_id",
        string="Customer Capacity Details",
    )

    def _get_capacity_in_mbps_from_offer_line(self, line):
        capacity = line.capacity or 0.0
        if not capacity:
            return 0.0

        parameter = line.parameter if "parameter" in line._fields else "mb"

        if parameter == "gb":
            mb_value = self.env["ir.config_parameter"].sudo().get_param(
                "isp.mb_value",
                default="0",
            )
            try:
                mb_factor = float(mb_value)
            except (TypeError, ValueError):
                mb_factor = 0.0

            if mb_factor <= 0.0:
                raise ValidationError(
                    _("Please configure a positive 'MB Value' in Settings > ISP Configuration to convert GB capacities.")
                )

            return capacity * mb_factor

        return capacity

    @api.depends_context("uid")
    def _compute_realtime_capacity(self):
        Client = self.env["isp.client"].sudo()

        active_bandwidth_clients = Client.search([
            ("active", "=", True),
            ("client_type", "=", "bandwith"),
            ("pipeline_state", "=", "noc_confirm"),
        ])

        bandwidth_capacity = 0.0

        for client in active_bandwidth_clients:
            for line in client.offer_capacity_type_ids:
                bandwidth_capacity += self._get_capacity_in_mbps_from_offer_line(line)

        mac_capacity = 0.0
        free_capacity = 0.0

        for dashboard in self:
            dashboard.bandwidth_capacity = bandwidth_capacity
            dashboard.mac_capacity = mac_capacity
            dashboard.total_capacity = bandwidth_capacity + mac_capacity
            dashboard.free_capacity = free_capacity

    def action_open_bandwidth_customers(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Bandwidth Customers",
            "res_model": "kio.capacity.dashboard.customer",
            "view_mode": "tree,form",
            "domain": [
                ("dashboard_id", "=", self.id),
                ("client_type", "=", "bandwith"),
            ],
            "context": {
                "default_dashboard_id": self.id,
                "default_client_type": "bandwith",
            },
            "target": "current",
        }