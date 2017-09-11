# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL Invoice
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
{
    "name": "Project Git Hook",
    "version": "8.0.1",
    "author": "Patrik Dufresne Service Logiciel inc.",
    "category": 'Tools',
    "description": """

This module provide Gitlab Github integration for Project Tasks and Issues. When properly configured, Git commits are link to the right project issue or tasks.

To ease migration, a script is also provided.

If you have multiple database installed, you may need to add this module to server_wide_modules.

""",
    "depends": [
        'project',
        ],
    "data": [],
    'installable': True,
    'active': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
