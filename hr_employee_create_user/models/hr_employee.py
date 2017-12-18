# -*- coding: utf-8 -*-

from odoo import models, api


class ResUsersInherit(models.Model):
    _inherit = 'hr.employee'

    @api.multi
    def create_user(self):
        # TODO may need rework creation of login to use only ascii.
        user_id = self.env['res.users'].create({
            'name': self.name,
            'login': self.work_email or self.name.replace(' ', '.').lower()
        })
        self.user_id = user_id
        self.address_home_id = user_id.partner_id.id
