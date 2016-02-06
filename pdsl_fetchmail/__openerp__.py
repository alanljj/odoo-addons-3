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
    "author": "Patrik Dufresne Service Logiciel inc.",
    "category": 'Tools',
    "description": """

This module allows the fetchmail module to operate on contracts. 

Contracts are created as incoming contracts, with the partner that has the
email's sender address along with all the partner's financial settings.

A partner is created from data inside the mail (json).

This module is compatible with OpenERP 8.0.

Known issues: not safe for use within a multicompany database.

* Create an incoming mail server
* Create an outgoing mail server (with the same address)
* Your Compagnie's email should match the incoming mail server address. It's used for Reply-To:
* One Sales Team should match the incoming mail address. Project -> Projects -> Create. Set Email Alias
* A second Sales Team should match the incoming mail address. Project -> Projects -> Create. Set Email Alias
* Outgoing mail interval should be changed: Settings -> Technical -> Scheduler -> Scheduled Actions -> Email Queue Manager
* Verify your catch all alias: Settings -> Technical -> Parameters -> System Parameters. Make sure you have "mail.catchall.domain" and "mail.catchall.alias" 

""",
    "depends": [
        'fetchmail',
        'crm',
        'account',
        'project_issue',
        ],
    "data": [
        'pdsl_crm_lead.xml',
        'pdsl_project_issue.xml',
        ],
    'installable': True,
    'active': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
