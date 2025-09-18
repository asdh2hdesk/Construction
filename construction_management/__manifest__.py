{
    'name': 'Construction Management',
    'version': '18.0.1.0',
    'category': 'Construction',
    'summary': 'Manage construction projects, BOQ, progress billing, DPR, and costs',
    'author': 'Megha',
    'depends': [
        'base',
        'mail',
        'project',
        'sale',
        'purchase',
        'stock',
        # 'account_asset',
        'hr_timesheet',
        'maintenance',
        'hr_contract',
    ],
    'data': [
        # 'security/security.xml',
        'security/ir.model.access.csv',
        'views/construction_project_views.xml',
        'views/construction_boq_views.xml',
        # 'views/construction_progress_views.xml',
        'views/dpr.xml',
        'views/construction_quality_views.xml',
        'views/equipment.xml',
        'views/employee.xml',
        'views/project_timeline.xml',
        'views/construction_inventory.xml',
        'views/dashboard_menu.xml'
    ],
    'assets': {
            'web.assets_backend': [
                'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
                'construction_management/static/src/css/construction_dashboard.css',
                'construction_management/static/src/js/construction_dashboard.js',
                'construction_management/static/src/js/individual_dashboard.js',
                'construction_management/static/src/css/individual_dashboard.css',

                'construction_management/static/src/xml/construction_dashboard_views.xml',
                'construction_management/static/src/xml/individual_dashboard.xml'
            ],
        },
    'installable': True,
    'application': True,
}
