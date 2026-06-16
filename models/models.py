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
