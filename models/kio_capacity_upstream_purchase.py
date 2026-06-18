# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KioCapacityUpstreamPurchase(models.Model):
    _name = "kio.capacity.upstream.purchase"
    _description = "KIO Upstream Capacity Purchase"
    _order = "sequence, provider_id, capacity_item, purchase_date desc, id desc"
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
    )
    provider_id = fields.Many2one(
        "res.partner",
        string="Provider",
        required=True,
        index=True,
    )
    capacity_item = fields.Char(
        string="Capacity Item",
        required=True,
        index=True,
        help="Example: Internet Bandwidth, NTTN Capacity, IP Transit.",
    )
    purchased_capacity = fields.Float(
        string="Purchased Capacity (Mbps)",
        required=True,
        default=0.0,
    )
    price = fields.Float(
        string="Price",
        default=0.0,
    )
    purchase_date = fields.Date(
        string="Purchase Date",
        default=fields.Date.context_today,
        required=True,
    )
    active = fields.Boolean(string="Active Status", default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", "New") == "New":
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "kio.capacity.upstream.purchase"
                ) or "New"
        return super().create(vals_list)

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

    @api.constrains("purchased_capacity", "price")
    def _check_purchased_capacity(self):
        for record in self:
            if record.purchased_capacity < 0:
                raise ValidationError("Purchased Capacity (Mbps) cannot be negative.")
            if record.price < 0:
                raise ValidationError("Price cannot be negative.")
