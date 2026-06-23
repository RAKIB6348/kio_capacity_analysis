# -*- coding: utf-8 -*-

import logging
from calendar import monthrange

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class KioCapacityDashboard(models.Model):
    _name = "kio.capacity.dashboard"
    _description = "KIO Capacity Dashboard"

    name = fields.Char(default="Capacity Overview", required=True)

    total_upstream_capacity = fields.Float(
        string="Total Upstream Capacity",
        compute="_compute_realtime_capacity",
        digits=(16, 2),
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
        date_from, date_to = self._get_default_upstream_capacity_date_range()
        return self._get_total_active_upstream_capacity(date_from=date_from, date_to=date_to)

    @api.model
    def _get_default_upstream_capacity_date_range(self):
        today = fields.Date.context_today(self)
        date_from = today.replace(day=1)
        date_to = today.replace(day=monthrange(today.year, today.month)[1])
        return fields.Date.to_string(date_from), fields.Date.to_string(date_to)

    @api.model
    def _get_upstream_vendor_bill_line_domain(self, date_from=False, date_to=False):
        domain = [
            ("move_id.move_type", "=", "in_invoice"),
            ("move_id.state", "!=", "cancel"),
            ("display_type", "=", "product"),
            ("product_id.product_tmpl_id.detailed_type", "=", "service"),
            ("product_id.product_tmpl_id.is_upstream_service", "=", True),
        ]
        if date_from:
            domain.append(("move_id.invoice_date", ">=", date_from))
        if date_to:
            domain.append(("move_id.invoice_date", "<=", date_to))
        return domain

    @api.model
    def _get_total_active_upstream_capacity(self, date_from=False, date_to=False):
        grouped_capacity = self.env["account.move.line"].sudo().read_group(
            self._get_upstream_vendor_bill_line_domain(date_from=date_from, date_to=date_to),
            ["quantity:sum"],
            [],
        )
        if not grouped_capacity:
            return 0.0
        return grouped_capacity[0].get("quantity", 0.0) or 0.0

    @api.model
    def get_total_active_upstream_capacity(self, date_from=False, date_to=False):
        return self._get_total_active_upstream_capacity(date_from=date_from, date_to=date_to)

    def _get_first_existing_field(self, model, field_names):
        for field_name in field_names:
            if field_name in model._fields:
                return field_name
        return False

    def _get_client_amount_from_fields(self, client, field_names):
        for field_name in field_names:
            if field_name in client._fields:
                return getattr(client, field_name) or 0.0
        return 0.0

    def _get_client_monthly_revenue(self, client):
        revenue = self._get_client_amount_from_fields(client, [
            "offer_total_price",
            "monthly_bill",
            "monthly_fee",
            "monthly_amount",
            "recurring_price",
            "package_price",
            "bill_amount",
        ])
        if revenue:
            return revenue

        if "offer_capacity_type_ids" not in client._fields:
            return 0.0

        offer_lines = client.offer_capacity_type_ids
        for field_name in ("offer_total_price", "total_price", "offer_price", "price"):
            if offer_lines and field_name in offer_lines._fields:
                return sum(offer_lines.mapped(field_name))
        return 0.0

    def _get_client_current_usage(self, client):
        return self._get_client_amount_from_fields(client, [
            "current_usage",
            "used_capacity",
            "usage_capacity",
            "consumed_capacity",
        ])

    def _get_client_package_info(self, client):
        package_field = self._get_first_existing_field(client, [
            "package_id",
            "internet_package_id",
            "customer_package_id",
            "service_package_id",
            "package_product_id",
            "product_id",
            "plan_id",
            "offer_id",
        ])
        if package_field:
            package = getattr(client, package_field)
            if package:
                return {
                    "id": "%s_%s" % (package_field, package.id),
                    "name": package.display_name,
                    "active": package.active if "active" in package._fields else True,
                }

        if "offer_capacity_type_ids" in client._fields and client.offer_capacity_type_ids:
            names = [line.display_name for line in client.offer_capacity_type_ids if line.display_name]
            package_name = ", ".join(names) if names else "Customer Package"
            return {
                "id": "offer_capacity_%s" % package_name,
                "name": package_name,
                "active": True,
            }

        return {
            "id": "unassigned",
            "name": "Unassigned Package",
            "active": True,
        }

    def _get_downstream_client_domain(self, date_from=False, date_to=False):
        Client = self.env["isp.client"].sudo()
        domain = []
        if "active" in Client._fields:
            domain.append(("active", "=", True))
        if "client_type" in Client._fields:
            domain.append(("client_type", "=", "bandwith"))
        if "pipeline_state" in Client._fields:
            domain.append(("pipeline_state", "=", "noc_confirm"))

        date_field = self._get_first_existing_field(Client, [
            "confirmed_date",
            "noc_confirmed_date",
            "noc_confirm_date",
            "activation_date",
            "create_date",
        ])
        if date_field and date_from:
            domain.append((date_field, ">=", date_from))
        if date_field and date_to:
            domain.append((date_field, "<=", date_to))
        return domain

    @api.model
    def get_downstream_capacity_dashboard_data(self, date_from=False, date_to=False):
        clients = self.env["isp.client"].sudo().search(
            self._get_downstream_client_domain(date_from=date_from, date_to=date_to),
            order="display_name asc, id asc",
        )

        packages = {}
        total_capacity = 0.0
        total_revenue = 0.0

        for client in clients:
            allocated_capacity, _base_capacity, _upgrade_capacity, _downgrade_capacity = (
                self._get_client_realtime_capacity(client)
            )
            current_usage = self._get_client_current_usage(client)
            monthly_revenue = self._get_client_monthly_revenue(client)
            remaining_capacity = max(allocated_capacity - current_usage, 0.0)
            package = self._get_client_package_info(client)

            if package["id"] not in packages:
                packages[package["id"]] = {
                    "packageId": package["id"],
                    "packageName": package["name"],
                    "active": package["active"],
                    "customerCount": 0,
                    "allocatedCapacity": 0.0,
                    "monthlyRevenue": 0.0,
                    "clientIds": [],
                    "customers": [],
                }

            package_row = packages[package["id"]]
            package_row["customerCount"] += 1
            package_row["allocatedCapacity"] += allocated_capacity
            package_row["monthlyRevenue"] += monthly_revenue
            package_row["clientIds"].append(client.id)
            package_row["customers"].append({
                "id": client.id,
                "name": client.display_name,
                "package": package["name"],
                "allocatedCapacity": allocated_capacity,
                "currentUsage": current_usage,
                "remainingCapacity": remaining_capacity,
                "monthlyBill": monthly_revenue,
                "status": "Active"
                if ("active" not in client._fields or client.active)
                else "Suspended",
            })

            total_capacity += allocated_capacity
            total_revenue += monthly_revenue

        package_rows = []
        for package in packages.values():
            package["averageCapacity"] = (
                package["allocatedCapacity"] / package["customerCount"]
                if package["customerCount"]
                else 0.0
            )
            package_rows.append(package)

        package_rows.sort(key=lambda row: row["packageName"].lower())

        return {
            "summary": {
                "totalActiveCustomers": len(clients),
                "totalAllocatedCapacity": total_capacity,
                "totalPackages": len(package_rows),
                "totalMonthlyRevenue": total_revenue,
            },
            "packages": package_rows,
        }

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

    def action_open_downstream_capacity_dashboard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "name": "Downstream Capacity Dashboard",
            "tag": "kio_capacity_analysis.downstream_capacity_dashboard",
            "target": "current",
        }
