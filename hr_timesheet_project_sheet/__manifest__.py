# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Patrik Dufresne
#    Copyright 2017 Patrik Dufresne Service Logiciel inc.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Project Timesheets',
    'version': '10.0.4',
    'category': 'Human Resources',
    'sequence': 80,
    'summary': 'Timesheets, Activities',
    'description': """This module provide a different way to manage time sheet per project instead of employees. It allows a manager to create timesheets for a specific project. For our specific need, this module also add begin, end time. Employee categories into timesheet.""",
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
        "report/report_timesheet_templates.xml",
        'data/hr_timesheet_project_sheet_data.xml',
        'data/hr_timesheet_action_data.xml',
        'data/hr_timesheet_employee_tag.xml',
        'views/hr_analytic_timesheet.xml',
        'views/hr_timesheet_project_sheet_templates.xml',
        'views/hr_timesheet_project_sheet_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'qweb': ['static/src/xml/timesheet.xml', ],
    'license': 'AGPL-3',
}
