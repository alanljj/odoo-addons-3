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
    "name": "PDSL Invoices",
    "version": "8.0.1",
    "author": "Patrik Dufresne",
    "category": 'Tools',
    "description": """

This module provide a custom invoice model.

This module is compatible with OpenERP 8.0.

""",
    "depends": [
        'account',
        ],
    "data": [
        'pdsl_invoice_data.xml',
        'views/report_invoice.xml',
        ],
    'installable': True,
    'active': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
