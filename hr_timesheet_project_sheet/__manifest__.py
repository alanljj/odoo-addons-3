# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Project Timesheets',
    'version': '10.0.3',
    'category': 'Human Resources',
    'sequence': 80,
    'summary': 'Timesheets, Activities',
    'description': """TODO""",
    'author': 'Patrik Dufresne',
    'website': 'http://www.patrikdufresne.com',
    'company': 'Patrik Dufresne Service Logiciel inc.',
    'depends': [
        'hr_timesheet',
        'project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_timesheet_project_sheet_security.xml',
        'data/hr_timesheet_project_sheet_data.xml',
        'views/hr_analytic_timesheet.xml',
        'views/hr_timesheet_project_sheet_templates.xml',
        'views/hr_timesheet_project_sheet_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'qweb': ['static/src/xml/timesheet.xml', ],
}
