# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrTimesheetCurrentOpen(models.TransientModel):
    _name = 'hr.timesheet.current.open'
    _description = 'hr.timesheet.current.open'

    @api.model
    def open_timesheet(self):
        view_type = 'form,tree'

        sheets = self.env['hr_timesheet_project_sheet.sheet'].search([('state', 'in', ('draft', 'new')),
                                                           ('date_from', '<=', fields.Date.today()),
                                                           ('date_to', '>=', fields.Date.today())])
        if len(sheets) > 1:
            view_type = 'tree,form'
            domain = "[('id', 'in', " + str(sheets.ids) + ")]"
        else:
            domain = "[]"
        value = {
            'domain': domain,
            'name': _('Open Timesheet'),
            'view_type': 'form',
            'view_mode': view_type,
            'res_model': 'hr_timesheet_project_sheet.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        if len(sheets) == 1:
            value['res_id'] = sheets.ids[0]
        return value
