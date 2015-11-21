# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL fetchmail addons
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
{
    "name": "PDSL Fetchmail",
    "version": "8.0.1",
    "author": "Patrik Dufresne",
    "category": 'Tools',
    "description": """

This module allows the fetchmail module to operate on contracts. 

Contracts are created as incoming contracts, with the partner that has the
email's sender address along with all the partner's financial settings.

A partner is created from data inside the mail (json).

This module is compatible with OpenERP 8.0.

Known issues: not safe for use within a multicompany database.
""",
    "depends": [
        'fetchmail',
        'crm',
        'account'
        ],
    "data": [
        'pdsl_fetchmail_confirm_email_template.xml',
        'pdsl_crm_lead.xml'
        ],
    'installable': True,
    'active': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
