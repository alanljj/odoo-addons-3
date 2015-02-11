# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2012 Therp BV (<http://therp.nl>).
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
    "name": "PDSL Fetchmail",
    "version": "0.1",
    "author": "Patrik Dufresne",
    "category": 'Tools',
    "description": """

This module allows the fetchmail module to operate on contracts. 

Contracts are created as incoming contracts, with the partner that has the
email's sender address along with all the partner's financial settings.

A partner is created from data inside the mail (json).

This module is compatible with OpenERP 7.0.

Known issues: not safe for use within a multicompany database.
""",
    "depends": [
        'fetchmail',
        'project_issue',
        'account'
        ],
    "data": [
        'pdsl_fetchmail_confirm_email_template.xml',
        'pdsl_project_data.xml'
        ],
    'installable': True,
    'active': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
