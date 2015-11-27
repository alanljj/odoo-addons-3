# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL Invoice
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
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
