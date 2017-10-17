# -*- coding: utf-8 -*-
# Copyright(C) 2017 Patrik Dufresne Service Logiciel inc.
# (http://www.patrikdufresne.com).
from dateutil.parser import parse
from email.message import Message
import logging
import re
from werkzeug.exceptions import BadRequest

from openerp import http, SUPERUSER_ID  # @UnresolvedImport
import openerp
from openerp.addons.mail.mail_message import decode  # @UnresolvedImport
from openerp.http import db_monodb
from openerp.osv import osv
from openerp.tools import html_escape

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
            mail_thread.message_process_git_commits(cr, SUPERUSER_ID, req.jsonrequest, context={})
        return True


class MailThread(osv.AbstractModel):
    """ Update MailThread to add the feature of bounced emails and replied emails
    in message_process. """
    _name = 'mail.thread'
    _inherit = ['mail.thread']

    def message_process_git_commits(self, cr, uid, data, context=None):
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

        context = context or {}
        context['commits'] = True

        # For each commit received, process it as a new email message.
        thread_ids = []
        for msg_txt in msg_from_commits(data):
            msg = self.message_parse(
                cr, uid, msg_txt, save_original=False, context=context)
            routes = self.message_route(
                cr, uid, msg_txt, msg, context=context)
            if not routes:
                _logger.info('git-hook Message-Id %s: cannot be routed', msg['message_id'])
                continue
            thread_id = self.message_route_process(
                cr, uid, msg_txt, msg, routes, context=context)
            thread_ids.append(thread_id)
        return thread_ids

    def message_route_check_task_code(self, cr, uid, message, message_dict, model=None, thread_id=None,
                                      custom_values=None, context=None):
        """
        Check if the given message has reference to a task code.
        """
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')
        body = message_dict.get('body')
        task_code_match = task_code_re.findall(body)

        # Check if the mail matches a task code.
        routes = []
        if task_code_match:
            model = 'project.task'
            thread_ids = self.pool[model].search(
                cr, uid, [('code', 'in', task_code_match)], context=context)
            for thread_id in thread_ids:
                route = self.message_route_verify(
                    cr, uid, message, message_dict,
                    (model, thread_id, custom_values, uid, False),
                    update_author=True, assert_model=False, create_fallback=True, context=context)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: referenced: %s thread_id: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, model, thread_id, custom_values, uid)
                    routes.append(route)
        return routes

    def message_route(self, cr, uid, message, message_dict, model=None, thread_id=None,
                      custom_values=None, context=None):
        context = context or {}

        # Execute new routing base on message content.
        routes = self.message_route_check_task_code(
            cr, uid, message, message_dict, model, thread_id, custom_values, context)

        if context.get('commits', False):
            # When handling commits message, don't fail if other message_route are not found.
            try:
                routes.extend(super(MailThread, self).message_route(cr, uid, message, message_dict, model, thread_id, custom_values, context))
            except ValueError:
                pass
        else:
            # Call original and let exception propagate.
            routes.extend(super(MailThread, self).message_route(cr, uid, message, message_dict, model, thread_id, custom_values, context))
        return routes
