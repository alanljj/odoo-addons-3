# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL Invoice
# Copyright(C) 2017 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
from openerp import models
from openerp import api

class account_invoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'
    
    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        return self.env['report'].get_action(self, 'pdsl_invoice.report_invoice')