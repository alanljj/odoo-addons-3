# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Patrik Dufresne
#    Copyright 2017 Patrik Dufresne Service Logiciel inc.
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
