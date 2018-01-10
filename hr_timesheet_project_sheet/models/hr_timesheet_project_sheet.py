# -*- coding: utf-8 -*-


import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.tools.sql import drop_view_if_exists
from odoo.exceptions import UserError, ValidationError


class HrTimesheetSheet(models.Model):
    _name = "hr_timesheet_project_sheet.sheet"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _table = 'hr_timesheet_project_sheet_sheet'
    _order = "id desc"
    _description = "Timesheet"

    name = fields.Char(string="Event Name", states={'confirm': [('readonly', True)], 'done': [('readonly', True)]}, help="The event name, You may include reference to PO number in this field.")
    project_id = fields.Many2one('project.project', string='Project', required=True, readonly=True, states={'new': [('readonly', False)]})
    date_from = fields.Date(string='Date From', required=True,
        index=True, readonly=True, states={'new': [('readonly', False)]})
    date_to = fields.Date(string='Date To', required=True,
        index=True, readonly=True, states={'new': [('readonly', False)]})
    timesheet_ids = fields.One2many('account.analytic.line', 'project_sheet_id',
        string='Timesheet lines',
        readonly=True, states={
            'draft': [('readonly', False)],
            'new': [('readonly', False)]})
    # state is created in 'new', automatically goes to 'draft' when created. Then 'new' is never used again ...
    # (=> 'new' is completely useless)
    state = fields.Selection([
        ('new', 'New'),
        ('draft', 'Open'),
        ('confirm', 'Waiting Approval'),
        ('done', 'Approved')], default='new', track_visibility='onchange',
        string='Status', required=True, readonly=True, index=True,
        help=' * The \'Open\' status is used when a user is encoding a new and unconfirmed timesheet. '
             '\n* The \'Waiting Approval\' status is used to confirm the timesheet by user. '
             '\n* The \'Approved\' status is used when the users timesheet is accepted by his/her senior.')
    account_ids = fields.One2many('hr_timesheet_project_sheet.sheet.account', 'project_sheet_id', string='Analytic accounts', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    contact_id = fields.Many2one('res.partner', string='Remote Contact', store=True, readonly=False)
    location = fields.Char(string="Location", help="Short description describing the location of the event.", store=True, readonly=False)

    @api.constrains('date_to', 'date_from', 'project_id')
    def _check_sheet_date(self, forced_project_id=False):
        for sheet in self:
            new_project_id = forced_project_id or sheet.project_id and sheet.project_id.id
            if new_project_id:
                self.env.cr.execute('''
                    SELECT id
                    FROM hr_timesheet_project_sheet_sheet
                    WHERE (date_from <= %s and %s <= date_to)
                        AND project_id=%s
                        AND id <> %s''',
                    (sheet.date_to, sheet.date_from, new_project_id, sheet.id))
                if any(self.env.cr.fetchall()):
                    raise ValidationError(_('You cannot have 2 timesheets for the same project that overlap!'))

    def copy(self, *args, **argv):
        raise UserError(_('You cannot duplicate a timesheet.'))

    @api.model
    def create(self, vals):
        res = super(HrTimesheetSheet, self).create(vals)
        res.write({'state': 'draft'})
        return res

    @api.multi
    def action_timesheet_draft(self):
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            raise UserError(_('Only an HR Officer or Manager can refuse timesheets or reset them to draft.'))
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_timesheet_confirm(self):
        self.write({'state': 'confirm'})
        return True

    @api.multi
    def action_timesheet_done(self):
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            raise UserError(_('Only an HR Officer or Manager can approve timesheets.'))
        if self.filtered(lambda sheet: sheet.state != 'confirm'):
            raise UserError(_("Cannot approve a non-submitted timesheet."))
        self.write({'state': 'done'})

    @api.multi
    def name_get(self):
        # week number according to ISO 8601 Calendar
        return [(r['id'], _('Week ') + str(datetime.strptime(r['date_from'], '%Y-%m-%d').isocalendar()[1]))
            for r in self.read(['date_from'], load='_classic_write')]

    @api.multi
    def unlink(self):
        sheets = self.read(['state'])
        for sheet in sheets:
            if sheet['state'] in ('confirm', 'done'):
                raise UserError(_('You cannot delete a timesheet which is already confirmed.'))

        analytic_timesheet_toremove = self.env['account.analytic.line']
        for sheet in self:
            analytic_timesheet_toremove += sheet.timesheet_ids.filtered(lambda t: not t.task_id)
        analytic_timesheet_toremove.unlink()

        return super(HrTimesheetSheet, self).unlink()

    # ------------------------------------------------
    # OpenChatter methods and notifications
    # ------------------------------------------------

    @api.multi
    def _track_subtype(self, init_values):
        if self:
            record = self[0]
            if 'state' in init_values and record.state == 'confirm':
                return 'hr_timesheet_project_sheet.mt_timesheet_confirmed'
            elif 'state' in init_values and record.state == 'done':
                return 'hr_timesheet_project_sheet.mt_timesheet_approved'
        return super(HrTimesheetSheet, self)._track_subtype(init_values)

    #@api.model
    #def _needaction_domain_get(self):
    #    empids = self.env['hr.employee'].search([('parent_id.user_id', '=', self.env.uid)])
    #    if not empids:
    #        return False
    #    return ['&', ('state', '=', 'confirm'), ('employee_id', 'in', empids.ids)]


class HrTimesheetSheetSheetAccount(models.Model):
    _name = "hr_timesheet_project_sheet.sheet.account"
    _description = "Timesheets by Period"
    _auto = False
    _order = 'name'

    name = fields.Many2one('account.analytic.account', string='Project / Analytic Account', readonly=True)
    project_sheet_id = fields.Many2one('hr_timesheet_project_sheet.sheet', string='Sheet', readonly=True)
    total = fields.Float('Total Time', digits=(16, 2), readonly=True)

    # still seing _depends in BaseModel, ok to leave this as is?
    _depends = {
        'account.analytic.line': ['account_id', 'date', 'unit_amount', 'project_id'],
        'hr_timesheet_project_sheet.sheet': ['date_from', 'date_to', 'project_id'],
    }

    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, 'hr_timesheet_project_sheet_sheet_account')
        self._cr.execute("""create view hr_timesheet_project_sheet_sheet_account as (
            select
                min(l.id) as id,
                l.account_id as name,
                s.id as project_sheet_id,
                sum(l.unit_amount) as total
            from
                account_analytic_line l
                    LEFT JOIN hr_timesheet_project_sheet_sheet s
                        ON (s.date_to >= l.date
                            AND s.date_from <= l.date
                            AND s.project_id = l.project_id)
            group by l.account_id, s.id
        )""")
