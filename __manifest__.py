# -*- coding: utf-8 -*-
{
    'name': "KIO Capacity Analysis",
    'summary': "Capacity analysis kanban dashboard",
    'description': "Capacity analysis dashboard for KIO operations.",
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Operations',
    'version': '17.0.1.0.0',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/capacity_dashboard_data.xml',
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kio_capacity_analysis/static/src/scss/capacity_dashboard.scss',
        ],
    },
    'demo': [
        'demo/demo.xml',
    ],
}
