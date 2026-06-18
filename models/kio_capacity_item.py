# -*- coding: utf-8 -*-

from odoo import fields, models


class KioCapacityItem(models.Model):
    _name = "kio.capacity.item"
    _description = "KIO Capacity Item"
    _order = "sequence, name"
    _sql_constraints = [
        (
            "name_unique",
            "unique(name)",
            "Capacity Item name must be unique.",
        ),
    ]

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
