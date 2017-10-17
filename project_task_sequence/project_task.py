# -*- coding: utf-8 -*-
# Copyright(C) 2017 Patrik Dufresne Service Logiciel inc. (http://www.patrikdufresne.com).

from openerp import SUPERUSER_ID  # @UnresolvedImport
from openerp import api  # @UnresolvedImport
from openerp.osv import osv, fields  # @UnresolvedImport


class project_task(osv.Model):
    _inherit = 'project.task'
    _columns = {
        'task_code': fields.char('Code', required=False, copy=False, readonly=True),
        'code': fields.char('Code', required=True, copy=False, readonly=True)
    }
    _defaults = {
        'code': lambda obj, cr, uid, context: '/',
    }

    @api.v7
    def create(self, cr, uid, vals, context=None):
        if vals.get('code', '/') == '/':
            vals['code'] = self.pool.get('ir.sequence').get(cr, uid, 'project.task') or '/'
            vals['task_code'] = vals['code']
        return super(project_task, self).create(cr, uid, vals, context=context)

    def init(self, cr):
        # set task_code if not defined.
        ids = self.search(cr, SUPERUSER_ID, [('code', '=', '/')])
        for task in self.browse(cr, SUPERUSER_ID, ids):
            if task.task_code and task.task_code != '/':
                code = task.task_code
            else:
                code = self.pool.get('ir.sequence').get(cr, SUPERUSER_ID, 'project.task') or '/'
            task.write({'task_code': code, 'code': code})

        sup = super(project_task, self)
        if hasattr(sup, 'init'):
            sup.init(cr)
