# -*- coding: utf-8 -*-
# from odoo import http


# class KioCapacityAnalysis(http.Controller):
#     @http.route('/kio_capacity_analysis/kio_capacity_analysis', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/kio_capacity_analysis/kio_capacity_analysis/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('kio_capacity_analysis.listing', {
#             'root': '/kio_capacity_analysis/kio_capacity_analysis',
#             'objects': http.request.env['kio_capacity_analysis.kio_capacity_analysis'].search([]),
#         })

#     @http.route('/kio_capacity_analysis/kio_capacity_analysis/objects/<model("kio_capacity_analysis.kio_capacity_analysis"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('kio_capacity_analysis.object', {
#             'object': obj
#         })

