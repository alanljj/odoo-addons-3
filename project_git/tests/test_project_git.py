# -*- coding: utf-8 -*-
# Copyright(C) 2017 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
import pkg_resources
import urllib2

from openerp.tests.common import PORT
import openerp.tests.common


class TestProjectGit(openerp.tests.common.HttpCase):

    def setUp(self):
        super(TestProjectGit, self).setUp()
        self.res_users = self.registry('res.users')
        self.project_task = self.registry('project.task')
        self.project_project = self.registry('project.project')
        self.mail_thread = self.registry('mail.thread')

        cr, uid = self.cr, self.uid

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        self.group_employee_id = group_employee_ref and group_employee_ref[1] or False

        # Find Project User group
        self.group_project_user_id = self.env.ref('project.group_project_user').id or False

        self.user_projectuser_id = self.res_users.create(cr, uid, {
            'name': 'Armande ProjectUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.projectuser@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_project_user_id])]
        }, {'no_reset_password': True})
        self.user_projectuser = self.res_users.browse(cr, uid, self.user_projectuser_id)
        self.partner_projectuser_id = self.user_projectuser.partner_id.id

        # Test 'Pigs' project
        self.project_pigs_id = self.project_project.create(cr, uid, {
            'name': 'Pigs',
            'privacy_visibility': 'public',
            'alias_name': 'project+pigs',
            'partner_id': self.partner_projectuser_id,
        }, {'mail_create_nolog': True})

        # Already-existing tasks in Pigs
        self.task_1_id = self.project_task.create(cr, uid, {
            'name': 'Pigs UserTask',
            'user_id': self.user_projectuser_id,
            'project_id': self.project_pigs_id,
            'code': 'TASK-1',
        }, {'mail_create_nolog': True})
        self.task_2_id = self.project_task.create(cr, uid, {
            'name': 'Pigs ManagerTask',
            'user_id': self.user_projectuser_id,
            'project_id': self.project_pigs_id,
            'code': 'TASK-2',
        }, {'mail_create_nolog': True})

    def _url_open_json(self, request_url, data_json):
        if request_url.startswith('/'):
            request_url = "http://localhost:%s%s" % (PORT, request_url)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        # data_json = json.dumps(data)
        # resp, content = Http().request(request_url, "POST", data_json, headers)
        req = urllib2.Request(request_url, data_json, headers)
        res = urllib2.urlopen(req, timeout=600)
        return res.read()

    def test_receive_invalid_data(self):
        """
        Test if an exception is raised when sending invalid json data.
        """
        self.opener.addheaders.append(('Content-Type', 'application/json'))
        self.opener.addheaders.append(('Accept', 'text/plain'))
        with self.assertRaises(urllib2.HTTPError):
            self._url_open_json("/git-hook", "invalid data")

    def test_receive_json(self):
        """
        Check if sending json data is ok and doesn't return an error.
        """
        data = pkg_resources.resource_string(__name__, 'gitlab_push.json')  # @UndefinedVariable
        self.opener.addheaders.append(('Content-Type', 'application/json'))
        self.opener.addheaders.append(('Accept', 'text/plain'))
        self._url_open_json("/git-hook", data)

    def test_message_process_git_commits_with_gitlab_push(self):
        """
        Test handling of push event.
        """
        cr, uid = self.cr, self.uid

        # Make sure a tasks exists
        tasks = self.project_task.search(cr, uid, [('code', '=', "TASK-1")])
        self.assertEqual(len(tasks), 1, 'task with task code TASK-1 should already exists.')

        self.opener.addheaders.append(('Content-Type', 'application/json'))
        self.opener.addheaders.append(('Accept', 'text/plain'))
        data = pkg_resources.resource_string(__name__, 'gitlab_push.json')  # @UndefinedVariable
        thread_ids = self.mail_thread.message_process_git_commits(cr, uid, data, context={})
        self.assertEqual(len(thread_ids), 1, 'Commit message should be added to TASK-1 thread')

    def test_message_process_git_commits_with_gitlab_repository_update(self):
        """
        Test handling of repository update.
        """
        cr, uid = self.cr, self.uid

        self.opener.addheaders.append(('Content-Type', 'application/json'))
        self.opener.addheaders.append(('Accept', 'text/plain'))
        data = pkg_resources.resource_string(__name__, 'gitlab_repository_update.json')  # @UndefinedVariable
        thread_ids = self.mail_thread.message_process_git_commits(cr, uid, data, context={})
        self.assertEqual(len(thread_ids), 0, 'Repository Update events should be ignored.')

    def test_message_process_git_commits_with_github_push(self):
        """
        Test handling of push event.
        """
        cr, uid = self.cr, self.uid

        # Make sure a tasks exists
        tasks = self.project_task.search(cr, uid, [('code', '=', "TASK-2")])
        self.assertEqual(len(tasks), 1, 'task with task code TASK-2 should already exists.')

        self.opener.addheaders.append(('Content-Type', 'application/json'))
        self.opener.addheaders.append(('Accept', 'text/plain'))
        data = pkg_resources.resource_string(__name__, 'github_push.json')  # @UndefinedVariable
        thread_ids = self.mail_thread.message_process_git_commits(cr, uid, data, context={})
        self.assertEqual(len(thread_ids), 2, 'Commit(s) message should be added to TASK-1 and TASK-2 thread')
