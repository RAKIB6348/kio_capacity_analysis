# -*- coding: utf-8 -*-

from odoo import fields, models


class KioCapacityDashboard(models.Model):
    _name = "kio.capacity.dashboard"
    _description = "KIO Capacity Dashboard"

    name = fields.Char(default="Capacity Overview", required=True)
    total_capacity = fields.Float(string="Total Capacity", default=0.0)
    bandwidth_capacity = fields.Float(string="Bandwidth Capacity", default=0.0)
    mac_capacity = fields.Float(string="MAC Capacity", default=0.0)
    free_capacity = fields.Float(string="Free Capacity", default=0.0)
    customer_line_ids = fields.One2many(
        "kio.capacity.dashboard.customer",
        "dashboard_id",
        string="Customer Capacity Details",
    )

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
        }
