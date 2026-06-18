# -*- coding: utf-8 -*-

from odoo import api, fields, models


class KioCapacityUpstreamPurchase(models.Model):
    _name = "kio.capacity.upstream.purchase"
    _description = "KIO Upstream Capacity Purchase"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, provider_id, purchase_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )
    sequence = fields.Integer(default=10)
    reference = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        copy=False,
        default="New",
        index=True,
        tracking=True,
    )
    provider_id = fields.Many2one(
        "res.partner",
        string="Provider",
        required=True,
        index=True,
        tracking=True,
    )
    responsible_user_id = fields.Many2one(
        "res.users",
        string="Responsible By",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    capacity_item = fields.Char(
        string="Capacity Items",
        compute="_compute_line_totals",
        store=True,
    )
    purchased_capacity = fields.Float(
        string="Purchased Capacity (Mbps)",
        compute="_compute_line_totals",
        store=True,
    )
    price = fields.Float(
        string="Total Price",
        compute="_compute_line_totals",
        store=True,
    )
    purchase_date = fields.Date(
        string="Purchase Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    active = fields.Boolean(string="Active Status", default=True, tracking=True)
    line_ids = fields.One2many(
        "kio.capacity.upstream.purchase.line",
        "purchase_id",
        string="Capacity Item Lines",
        copy=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", "New") == "New":
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "kio.capacity.upstream.purchase"
                ) or "New"
        return super().create(vals_list)

    @api.depends(
        "line_ids.capacity_item",
        "line_ids.purchased_capacity",
        "line_ids.price",
    )
    def _compute_line_totals(self):
        for record in self:
            items = [item for item in record.line_ids.mapped("capacity_item") if item]
            record.capacity_item = ", ".join(items) if items else ""
            record.purchased_capacity = sum(record.line_ids.mapped("purchased_capacity"))
            record.price = sum(record.line_ids.mapped("price"))

    @api.depends("reference", "provider_id", "capacity_item", "purchased_capacity")
    def _compute_name(self):
        for record in self:
            provider = record.provider_id.display_name or "Provider"
            item = record.capacity_item or "Capacity"
            capacity = record.purchased_capacity or 0.0
            record.name = "%s - %s - %s - %s Mbps" % (
                record.reference or "New",
                provider,
                item,
                capacity,
            )
