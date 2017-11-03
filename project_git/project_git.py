# -*- coding: utf-8 -*-
# Copyright(C) 2017 Patrik Dufresne Service Logiciel inc.
# (http://www.patrikdufresne.com).
from dateutil.parser import parse
from email.message import Message
import logging
import re
from werkzeug.exceptions import BadRequest

from openerp import http, SUPERUSER_ID  # @UnresolvedImport
from openerp import models, api  # @UnresolvedImport
import openerp
from openerp.addons.mail.mail_message import decode  # @UnresolvedImport
from openerp.http import db_monodb
from openerp.tools import html_escape
from openerp.osv import osv


try:
    import simplejson as json
except ImportError:
    import json  # noqa


_logger = logging.getLogger(__name__)

# Expression to identify task code.
task_code_re = re.compile("(TASK-[0-9]+)", re.UNICODE)


def decode_header(message, header, separator=' '):
    return separator.join(map(decode, filter(None, message.get_all(header, []))))


class GitController(http.Controller):  # @UndefinedVariable

    @http.route('/git-hook', type='json', auth='none')
    def receive(self, req):
        """
        End-Point to receive gitlab hook calls. Will append a message to any
        matching Task or Issue related to the commit.
        """
        # Get database registry from query fragment. When running multiple
        # database, the database info may come from the request or HTTP fragment.
        # When running only a single database, the database doesn't need to be
        # declare.
        dbname = req.db
        if not dbname:
            dbname = req.httprequest.args.get('db')
        if not dbname:
            dbname = db_monodb()
        if not dbname:
            return BadRequest()
        registry = openerp.registry(dbname)

        # Extract
        with registry.cursor() as cr:
            mail_thread = registry['mail.thread']
            mail_thread.git_process_commits(cr, SUPERUSER_ID, req.jsonrequest, context={})
        return True


class MailThread(osv.AbstractModel):
    """ Update MailThread to add the feature of bounced emails and replied emails
    in message_process. """
    _name = 'mail.thread'
    _inherit = ['mail.thread']

    def git_append_commit_message(self, cr, uid, thread_id, message_dict, context=None):
        """
        Append the given message to the tasks using a specific subtype.
        """
        context = dict(context or {})
        email_from = message_dict.get('from')
        model = context.get('thread_model', False) if self._name == 'mail.thread' else self._name

        # Find the right author
        author_ids = self._find_partner_from_emails(cr, uid, thread_id, [email_from], model=model, context=context)
        if author_ids:
            author_id = author_ids[0]
            message_dict['author_id'] = author_id

        return self.message_post(cr, uid, thread_id, subtype='project_git.mt_git_commit', context=context, **message_dict)

    def git_process_commits(self, cr, uid, data, context=None):
        """
        Specific implementation used to receive commit message from git hook
        and convert them into messages.
        """
        def _from(commit):
            if commit.get('author', False):
                return "%s <%s>" % (commit.get('author').get('name'), commit.get('author').get('email'))

        def _subject(commit):
            """Return the first line of the commit message."""
            return "Mention by %s in commit %s" % (commit.get('author', {}).get('name', ''), commit.get('id'))

        def _body(commit):
            body = "<p>"
            body += html_escape(commit['message']).replace('\r\n', '<br/>').replace('\r', '<br/>').replace('\n', '<br/>')
            body += "</p>"

            body += "<hr/>"

            body += "<h4>"
            body += "You can view, comment on, or merge this pull request online at:"
            body += "</h4>"
            body += "<p>&nbsp;&nbsp;"
            body += '<a href="%s">%s</a>' % (commit['url'], commit['id'])
            body += "</p>"

            # TODO include file changes

            return body

        def _date(commit):
            if commit.get('timestamp'):
                # Format
                # Fri, 8 Sep 2017 14:57:26 -0400
                d = parse(commit.get('timestamp'))
                return d.strftime('%a, %d %b %Y %H:%M:%S %z')

        def _message_id(commit):
            if commit.get('id'):
                return commit.get('id') + "@localhost"

        def msg_from_commits(data):
            """
            Convert git hook data into message to be process by the openerp
            mailing process.
            """
            # If data is a string, try to read it as a json.
            if hasattr(data, 'lower'):
                data = json.loads(data)

            messages = []
            commits = data.get('commits', [])
            for commit in commits:
                msg_txt = Message()
                msg_txt.add_header('Content-Type', 'text/html; charset="UTF-8"')
                msg_txt.add_header('Subject', _subject(commit))
                msg_txt.add_header('Date', _date(commit))
                msg_txt.add_header('From', _from(commit))
                msg_txt.add_header('Message-ID', _message_id(commit))
                msg_txt.set_payload(_body(commit))
                messages.append(msg_txt)
            return messages

        context = dict(context or {})

        # For each commit received, process it as a new message.
        msg_ids = []
        for msg_txt in msg_from_commits(data):
            msg = self.message_parse(
                cr, uid, msg_txt, save_original=False, context=context)

            # Try to find corresponding thread ids
            routes = self.git_find_threads(cr, uid, msg, context=context)
            if not routes:
                _logger.info('git-hook Message-Id %s: cannot be routed', msg['message_id'])
                continue

            # Append the commit message to all matching task.
            for model, thread_id in routes:
                context['thread_model'] = model
                msg_ids.append(self.git_append_commit_message(cr, uid, thread_id, msg, context=context))
                _logger.info('git-hook Message-Id %s: appended to thread_ids: %s', msg['message_id'], thread_id)

        return msg_ids

    def git_find_threads(self, cr, uid, message_dict, context=None):
        """
        Check if the given message has reference to a task code.
        """
        body = message_dict.get('body')
        task_codes = task_code_re.findall(body)
        routes = []
        if task_codes:
            thread_ids = self.pool['project.task'].search(
                cr, uid, [('code', 'in', task_codes)], context=context)
            routes.extend([('project.task', i) for i in thread_ids])
        return routes