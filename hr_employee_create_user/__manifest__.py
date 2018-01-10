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
    'name': 'Create User from Employee View',
    'version': '10.0.3',
    'description': 'This module ease the creation of user from employee view with a single button.',
    'category': 'Human Resources',
    'author': 'Patrik Dufresne',
    'website': 'http://www.patrikdufresne.com',
    'company': 'Patrik Dufresne Service Logiciel inc.',
    'depends': ['base', 'hr'],
    'data': ['views/hr_employee_view.xml'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
