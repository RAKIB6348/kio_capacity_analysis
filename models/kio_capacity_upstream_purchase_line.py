# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KioCapacityUpstreamPurchaseLine(models.Model):
    _name = "kio.capacity.upstream.purchase.line"
    _description = "KIO Upstream Capacity Purchase Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    purchase_id = fields.Many2one(
        "kio.capacity.upstream.purchase",
        string="Upstream Purchase",
        required=True,
        ondelete="cascade",
    )
    capacity_item_id = fields.Many2one(
        "kio.capacity.item",
        string="Capacity Item",
        required=True,
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
    total_price = fields.Float(
        string="Total Price",
        compute="_compute_total_price",
        store=True,
    )

    @api.depends("purchased_capacity", "price")
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.purchased_capacity * record.price

    @api.constrains("purchased_capacity", "price")
    def _check_positive_values(self):
        for record in self:
            if record.purchased_capacity < 0:
                raise ValidationError("Purchased Capacity (Mbps) cannot be negative.")
            if record.price < 0:
                raise ValidationError("Price cannot be negative.")
