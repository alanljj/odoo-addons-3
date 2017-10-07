# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL fetchmail addons
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
from collections import OrderedDict
import unittest

from pdsl_fetchmail.model.pdsl_fetchmail import _parse_body, _format_body


class Test(unittest.TestCase):

    def test_format_body(self):
        
        data = OrderedDict()
        data['action'] = 'support'
        data['email'] = 'ikus060@gmail.com'
        data['lang'] = 'fr'
        data['name'] = 'Patrik Dufresne'
        data['os'] = 'Windows XP'
        data['phone'] = '5149716442'
        data['product'] = 'minarca'
        data['subject'] = 'coucou6'
        data['version'] = 'null'
        data['message'] = 'coucou6'
        
        body = _format_body(data)
        self.assertEqual("""action: support
email: ikus060@gmail.com
lang: fr
name: Patrik Dufresne
os: Windows XP
phone: 5149716442
product: minarca
subject: coucou6
version: null

coucou6""", body)

    def test_parse_body(self):

        data = _parse_body("""action: support
email: ikus060@gmail.com
lang: fr
name: Patrik Dufresne
os: Windows XP
phone: 5149716442
product: minarca
subject: coucou6
version: null

coucou6""")
        self.assertEqual('support', data.get('action'))
        self.assertEqual('ikus060@gmail.com', data.get('email'))
        self.assertEqual('fr', data.get('lang'))
        self.assertEqual('Patrik Dufresne', data.get('name'))
        self.assertEqual('Windows XP', data.get('os'))
        self.assertEqual('5149716442', data.get('phone'))
        self.assertEqual('minarca', data.get('product'))
        self.assertEqual('coucou6', data.get('subject'))
        self.assertEqual('null', data.get('version'))
        self.assertEqual('coucou6', data.get('message'))


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
