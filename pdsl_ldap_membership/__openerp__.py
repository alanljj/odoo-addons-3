# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL fetchmail addons
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
{
    "name": "PDSL LDAP Membership",
    "version": "8.0.1",
    "author": "Patrik Dufresne Service Logiciel inc.",
    "category": 'Tools',
    "description": """

This modules is used to manage the creation of users into an LDAP according to
partner membership. The goal is to control partner access to your service.

""",
    "depends": [
        'membership',
        'auth_ldap',
        ],
    "data": [
        'pdsl_ldap_membership.xml',
        ],
    'installable': True,
    'active': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: