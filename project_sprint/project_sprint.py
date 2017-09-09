# -*- coding: utf-8 -*-
# Copyright(C) 2017 Patrik Dufresne Service Logiciel inc. (http://www.patrikdufresne.com).

from openerp.osv import osv, fields


class project_sprint(osv.Model):

    def set_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True

    def set_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancelled'}, context=context)
        return True

    def set_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'open'}, context=context)
        return True

    _name = 'project.sprint'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    def _task_count(self, cr, uid, ids, field_name, arg, context=None):
        task = self.pool['project.task']
        return {
            sprint_id: task.search_count(cr,uid, [('sprint_id', '=', sprint_id)], context=context)
            for sprint_id in ids
        }

    _columns = {
        'name': fields.char('Name', 264, required=True),
        'project_id': fields.many2one('project.project', 'Project',
                                      ondelete="cascade"),
        'description': fields.text('Description'),
        'datestart': fields.date('Start Date'),
        'dateend': fields.date('End Date'),
        'color': fields.integer('Color Index'),
        'members': fields.many2many('res.users', 'project_user_rel',
                                    'project_id', 'uid', 'Project Members',
                                    states={'close': [('readonly', True)],
                                            'cancelled': [('readonly', True)],
                                            }),
        'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority', select=True),
        'state': fields.selection([('draft', 'New'),
                                   ('open', 'In Progress'),
                                   ('cancelled', 'Cancelled'),
                                   ('done', 'Done')],
                                  'Status', required=True,),
        'user_id': fields.many2one('res.users', 'Assigned to'),
        'kanban_state': fields.selection([('normal', 'Normal'),
                                          ('blocked', 'Blocked'),
                                          ('done', 'Ready To Pull')],
                                         'Kanban State',
                                         help="""A task's kanban state indicate
                                                 special situations
                                                 affecting it:\n
                                               * Normal is the default
                                                 situation\n"
                                               * Blocked indicates something
                                                 is preventing the progress
                                                 of this task\n
                                               * Ready To Pull indicates the
                                                 task is ready to be pulled
                                                 to the next stage""",
                                         readonly=True, required=False),
        'task_ids': fields.one2many('project.task', 'sprint_id', 'Tasks'),
        'task_count': fields.function(_task_count, string='# Tasks', type='integer'),
    }
    _order = "datestart, id"

    def set_kanban_state_blocked(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'kanban_state': 'blocked'}, context=context)
        return False

    def set_kanban_state_normal(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'kanban_state': 'normal'}, context=context)
        return False

    def set_kanban_state_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'kanban_state': 'done'}, context=context)
        return False

    def set_priority(self, cr, uid, ids, priority, *args):
        return self.write(cr, uid, ids, {'priority': priority})

    def set_high_priority(self, cr, uid, ids, *args):
        return self.set_priority(cr, uid, ids, '2')

    def set_normal_priority(self, cr, uid, ids, *args):
        return self.set_priority(cr, uid, ids, '1')

    _defaults = {
        'state': 'draft',
        'priority': '1',
    }


class project_task(osv.Model):

    _inherit = 'project.task'

    _columns = {
        'sprint_id': fields.many2one('project.sprint', 'Sprint', ondelete="cascade"),
    }
