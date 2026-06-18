# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class KioCapacityDashboard(models.Model):
    _name = "kio.capacity.dashboard"
    _description = "KIO Capacity Dashboard"

    name = fields.Char(default="Capacity Overview", required=True)

    total_upstream_capacity = fields.Float(
        string="Total Upstream Capacity",
        compute="_compute_realtime_capacity",
        store=False,
    )

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
        compute="_compute_realtime_capacity",
        store=False,
    )

    downgrade_capacity = fields.Float(
        string="Downgrade Capacity",
        compute="_compute_realtime_capacity",
        store=False,
    )

    customer_line_ids = fields.One2many(
        "kio.capacity.dashboard.customer",
        "dashboard_id",
        string="Customer Capacity Details",
    )

    def _get_request_entered_capacity(self, request):
        entered_capacity = sum(request.line_ids.mapped("entered_capacity"))

        if not entered_capacity:
            entered_capacity = (
                request.entered_capacity_total
                or request.entered_capacity
                or 0.0
            )

        return entered_capacity

    def _get_client_realtime_capacity(self, client):
        ChangeRequest = self.env["isp.portal.change.request"].sudo()

        requests = ChangeRequest.search([
            ("client_id", "=", client.id),
            ("request_type", "in", ["upgrade", "downgrade"]),
        ], order="submitted_on asc, id asc")

        fallback_base_capacity = sum(client.offer_capacity_type_ids.mapped("capacity"))

        base_capacity = fallback_base_capacity
        upgrade_capacity = 0.0
        downgrade_capacity = 0.0

        if not requests:
            return base_capacity, base_capacity, 0.0, 0.0

        first_request = requests[0]

        base_capacity = (
                first_request.current_capacity_total
                or first_request.current_capacity
                or fallback_base_capacity
                or 0.0
        )

        for request in requests:
            entered_capacity = self._get_request_entered_capacity(request)

            if request.request_type == "upgrade":
                upgrade_capacity += max(entered_capacity, 0.0)

            elif request.request_type == "downgrade":
                downgrade_capacity += max(entered_capacity, 0.0)

            _logger.info(
                "[KIO Capacity Dashboard] Client=%s Request ID=%s Type=%s Current=%s Entered=%s",
                client.display_name,
                request.id,
                request.request_type,
                request.current_capacity_total or request.current_capacity or 0.0,
                entered_capacity,
            )

        final_capacity = base_capacity + upgrade_capacity - downgrade_capacity

        if final_capacity < 0:
            final_capacity = 0.0

        return final_capacity, base_capacity, upgrade_capacity, downgrade_capacity

    def _get_total_upstream_capacity(self):
        grouped_capacity = self.env["kio.capacity.upstream.purchase.line"].sudo().read_group(
            [("purchase_id.active", "=", True)],
            ["purchased_capacity:sum"],
            [],
        )
        if not grouped_capacity:
            return 0.0
        return grouped_capacity[0].get("purchased_capacity", 0.0) or 0.0

    @api.depends_context("uid")
    def _compute_realtime_capacity(self):
        Client = self.env["isp.client"].sudo()
        total_upstream_capacity = self._get_total_upstream_capacity()

        active_bandwidth_clients = Client.search([
            ("active", "=", True),
            ("client_type", "=", "bandwith"),
            ("pipeline_state", "=", "noc_confirm"),
        ])

        total_final_capacity = 0.0
        total_base_capacity = 0.0
        total_upgrade_capacity = 0.0
        total_downgrade_capacity = 0.0

        _logger.info(
            "[KIO Capacity Dashboard] Active NOC confirmed bandwidth clients found: %s",
            len(active_bandwidth_clients),
        )

        for client in active_bandwidth_clients:
            (
                client_final_capacity,
                client_base_capacity,
                client_upgrade_capacity,
                client_downgrade_capacity,
            ) = self._get_client_realtime_capacity(client)

            total_final_capacity += client_final_capacity
            total_base_capacity += client_base_capacity
            total_upgrade_capacity += client_upgrade_capacity
            total_downgrade_capacity += client_downgrade_capacity

            _logger.info(
                "[KIO Capacity Dashboard] Client=%s Base=%s Upgrade=%s Downgrade=%s Final=%s",
                client.display_name,
                client_base_capacity,
                client_upgrade_capacity,
                client_downgrade_capacity,
                client_final_capacity,
            )

        _logger.info(
            "[KIO Capacity Dashboard] Total Base=%s Total Upgrade=%s Total Downgrade=%s Total Final=%s",
            total_base_capacity,
            total_upgrade_capacity,
            total_downgrade_capacity,
            total_final_capacity,
        )

        for dashboard in self:
            dashboard.total_upstream_capacity = total_upstream_capacity
            dashboard.total_capacity = total_final_capacity
            dashboard.bandwidth_capacity = total_final_capacity
            dashboard.mac_capacity = 0.0
            dashboard.free_capacity = 0.0
            dashboard.upgrade_capacity = total_upgrade_capacity
            dashboard.downgrade_capacity = total_downgrade_capacity

    def action_open_upgrade_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Upgrade Capacity Requests",
            "res_model": "isp.portal.change.request",
            "view_mode": "tree,form",
            "domain": [
                ("request_type", "=", "upgrade"),
                ("client_id.active", "=", True),
                ("client_id.client_type", "=", "bandwith"),
            ],
            "context": {
                "create": False,
                "edit": False,
            },
            "target": "current",
        }

    def action_open_downgrade_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Downgrade Capacity Requests",
            "res_model": "isp.portal.change.request",
            "view_mode": "tree,form",
            "domain": [
                ("request_type", "=", "downgrade"),
                ("client_id.active", "=", True),
                ("client_id.client_type", "=", "bandwith"),
            ],
            "context": {
                "create": False,
                "edit": False,
            },
            "target": "current",
        }

    def action_open_bandwidth_customers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Active Bandwidth Customers",
            "res_model": "isp.client",
            "view_mode": "tree,form",
            "domain": [
                ("active", "=", True),
                ("client_type", "=", "bandwith"),
                ("pipeline_state", "=", "noc_confirm"),
            ],
            "context": {
                "default_client_type": "bandwith",
                "create": False,
                "edit": False,
            },
            "target": "current",
        }

    def action_open_upstream_purchases(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id(
            "kio_capacity_analysis.action_kio_capacity_client_dashboard"
        )
