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
from __future__ import division

from datetime import timedelta
import math

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


def float_time_convert(float_val):
    hours = math.floor(abs(float_val))
    mins = abs(float_val) - hours
    mins = round(mins * 60)
    if mins >= 60.0:
        hours = hours + 1
        mins = 0.0
    return '%02d:%02d' % (hours, mins)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model
    def _default_project(self):
        return self.env.context.get('project_id', None)

    project_sheet_id_computed = fields.Many2one('hr_timesheet_project_sheet.sheet', string='Sheet', compute='_compute_sheet', index=True,
        ondelete='cascade', search='_search_sheet')
    project_sheet_id = fields.Many2one('hr_timesheet_project_sheet.sheet', compute='_compute_sheet', string='Sheet', store=True)
    project_id = fields.Many2one(default=_default_project)
    employee_category = fields.Many2one(comodel_name='hr.employee.category', string="Employee Category")
    time_start = fields.Float(string='Begin', help='Begin time when the employee start working. This value will be used to compute the total number of hours worked.')
    time_stop = fields.Float(string='End', help='End time when the employee stop working. This value will be used to compute the total number of hours worked.')
    time_break = fields.Float(string='Break', help='Break time taken by the employee. This value will be used to compute the total number of hours worked.')

    @api.depends('date', 'user_id', 'project_id', 'project_sheet_id_computed.date_to', 'project_sheet_id_computed.date_from', 'project_sheet_id_computed.project_id')
    def _compute_sheet(self):
        """Links the timesheet line to the corresponding sheet
        """
        for ts_line in self:
            if not ts_line.project_id:
                continue
            sheets = self.env['hr_timesheet_project_sheet.sheet'].search(
                [('date_to', '>=', ts_line.date), ('date_from', '<=', ts_line.date),
                 ('project_id.id', '=', ts_line.project_id.id),
                 ('state', 'in', ['draft', 'new'])])
            if sheets:
                # [0] because only one sheet possible for a project between 2 dates
                ts_line.project_sheet_id_computed = sheets[0]
                ts_line.project_sheet_id = sheets[0]

    def _search_sheet(self, operator, value):
        assert operator == 'in'
        ids = []
        for ts in self.env['hr_timesheet_project_sheet.sheet'].browse(value):
            self._cr.execute("""
                    SELECT l.id
                        FROM account_analytic_line l
                    WHERE %(date_to)s >= l.date
                        AND %(date_from)s <= l.date
                        AND %(project_id)s = l.project_id
                    GROUP BY l.id""", {'date_from': ts.date_from,
                                       'date_to': ts.date_to,
                                       'project_id': ts.project_id.id, })
            ids.extend([row[0] for row in self._cr.fetchall()])
        return [('id', 'in', ids)]

    @api.multi
    def write(self, values):
        self._check_state()
        return super(AccountAnalyticLine, self).write(values)

    @api.multi
    def unlink(self):
        self._check_state()
        return super(AccountAnalyticLine, self).unlink()

    def _check_state(self):
        for line in self:
            if line.project_sheet_id and line.project_sheet_id.state not in ('draft', 'new'):
                raise UserError(_('You cannot modify an entry in a confirmed timesheet.'))
        return True

    @api.one
    @api.constrains('time_start', 'time_stop', 'unit_amount')
    def _check_time_start_stop(self):
        start = timedelta(hours=self.time_start)
        stop = timedelta(hours=self.time_stop)
        tbreak = timedelta(hours=self.time_break)
        if stop < start:
            raise exceptions.ValidationError(
                _('The beginning hour (%s) must '
                  'precede the ending hour (%s).') %
                (float_time_convert(self.time_start),
                 float_time_convert(self.time_stop))
            )
        hours = (stop - start - tbreak).seconds / 3600
        if (hours and
                float_compare(hours, self.unit_amount, precision_digits=4)):
            raise exceptions.ValidationError(
                _('The duration (%s) must be equal to the difference '
                  'between the hours (%s).') %
                (float_time_convert(self.unit_amount),
                 float_time_convert(hours))
            )
        # check if lines overlap
        if self.user_id:
            others = self.search([
                ('id', '!=', self.id),
                ('user_id', '=', self.user_id.id),
                ('date', '=', self.date),
                ('time_start', '<', self.time_stop),
                ('time_stop', '>', self.time_start),
            ])
            if others:
                message = _("Lines can't overlap:\n")
                message += '\n'.join(['%s - %s' %
                                      (float_time_convert(line.time_start),
                                       float_time_convert(line.time_stop))
                                      for line
                                      in (self + others).sorted(
                                          lambda l: l.time_start
                                      )])
                raise exceptions.ValidationError(message)

    @api.onchange('time_start', 'time_stop', 'time_break')
    def onchange_hours_start_stop(self):
        start = timedelta(hours=self.time_start)
        stop = timedelta(hours=self.time_stop)
        tbreak = timedelta(hours=self.time_break)
        if stop < start:
            return
        self.unit_amount = (stop - start - tbreak).seconds / 3600

    #@api.onchange('employee_category')
    #def onchange_place(self):
    #    res = {}
    #    if self.employee_category:
    #        res['domain'] = {'user_id': [('employee_ids.category_ids', 'in', self.employee_category)]}
    #    return res
