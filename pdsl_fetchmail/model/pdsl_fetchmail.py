# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL fetchmail addons
# Copyright(C) 2017 Patrik Dufresne Service Logiciel
# (http://www.patrikdufresne.com).
#
##############################################################################
import logging
import re
import time

from openerp import models  # @UnresolvedImport
from openerp import tools  # @UnresolvedImport
from openerp import api  # @UnresolvedImport
from openerp.addons.mail.mail_thread import mail_thread  # @UnresolvedImport

try:
    import simplejson as json
except ImportError:
    import json  # noqa


_logger = logging.getLogger(__name__)

# List of supported extra field.
EXTRA_FIELDS = ['name', 'email', 'lang', 'action', 'product', 'phone',
                'street', 'street2', 'city', 'state', 'country', 'zip']


# Regex pattern used to match fields in email.
pdsl_command_re = re.compile("^([a-z]+) *: *(.+)$", re.I + re.UNICODE)


def _format_body(data, filterout=[]):
    """
    Format dictionary object.
    """
    body = ""
    for key, value in data.items():
        if key in filterout:
            continue
        if key == 'message':
            continue
        body += "%s: %s\n" % (key, value)
    if data.get('message'):
        body += "\n"
        body += data['message']
    return body


def _parse_body(body):
    """
    Parse message body.
    """
    if not body:
        return False
    try:
        # Try to convert the body as Json.
        return json.loads(body)
    except:
        pass

    in_message = False
    data = dict()
    for line in body.splitlines():
        if not line:
            in_message = True
            continue
        if not in_message:
            (key, s, value) = line.partition(': ')
            data[key] = value
        elif data.get('message'):
            data['message'] += line
        else:
            data['message'] = line

    return data


# ----------------------------------------
# Patch Mail Thread
# ----------------------------------------


message_parse_orig = mail_thread.message_parse
message_post_orig = mail_thread.message_post


@api.cr_uid_ids_context
def message_parse(self, cr, uid, message, save_original=False, context=None):
    """
    Override to extract data from body and replace header value.
    """
    # Call original implementation to parse the RFC data.
    msg = message_parse_orig(self, cr, uid, message,
                             save_original=save_original, context=context)

    # Continue the parsing of the body.
    body = tools.html2plaintext(msg.get('body')) if msg.get('body') else ''
    extra_values = {}
    for line in body.split('\n'):
        line = line.strip()
        m = pdsl_command_re.match(line)
        if m and m.group(1).lower() in EXTRA_FIELDS:
            extra_values[m.group(1).lower()] = m.group(2)

    # Change context language
    lang = extra_values.get('lang', None)
    if lang:
        pool_lang = self.pool.get('res.lang')
        lang_ids = pool_lang.search(
            cr, uid, [('code', 'ilike', lang)], limit=1, context=context)
        if lang_ids and lang_ids[0]:
            lang_obj = pool_lang.browse(cr, uid, lang_ids[0], context=context)
            _logger.debug('language [%s] found as [%s]', lang, lang_obj.code)
            if lang_obj.code:
                # Set context language
                context['lang'] = lang_obj.code

    # Change email from
    email = extra_values.get('email', None)
    if email:
        # Remove any extra space. e.g.: foo@bar.com [3]
        email = email_from = re.search('[^ ]*', email).group(0)
        name = extra_values.get('name', None)
        if name:
            email_from = '%s <%s>' % (name, email)
        msg['email_from'] = email_from
        msg['from'] = email_from
        # Replace original from value.
        partner_obj = self.pool.get('res.partner')
        author_ids = partner_obj.search(
            cr, uid, [('email', 'ilike', email)], limit=1, context=context)
        if author_ids:
            msg['author_id'] = author_ids[0]

    msg.update(extra_values)
    return msg


@api.cr_uid_ids_context
def message_post(self, cr, uid, thread_id, context, **message_dict):
    """
    Override to remove invalid fields added by message_parse().
    """
    # Remove invalid fields to avoid warning.
    for key in EXTRA_FIELDS:
        message_dict.pop(key, None)
    # Call original implementation
    return message_post_orig(self, cr, uid, thread_id,
                             context=context, **message_dict)


# install override
mail_thread.message_parse = message_parse
mail_thread.message_post = message_post


class crm_lead(models.Model):
    """
    Enhance reception of mail to create CRM Lead with more data.
    """
    _name = 'crm.lead'
    _inherit = 'crm.lead'

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------

    def _pdsl_find_categ(self, cr, uid, action, context=None):
        """Search categories related to the mail."""
        tags_pool = self.pool.get('crm.case.categ')
        tag_ids = tags_pool.search(
            cr, uid, [('name', 'ilike', action)], limit=1, context=context)
        if not tag_ids or not tag_ids[0]:
            return False
        _logger.debug(
            "action [%s] found as category []categories [%s]",
            action, tag_ids[0])
        return tag_ids[0]

    def _pdsl_find_country_id(self, cr, uid, country, context=None):
        """ Return the appropriate country_id. """
        country_pool = self.pool.get('res.country')
        country_ids = country_pool.search(
            cr, uid, [('code', 'ilike', country)], limit=1, context=context)
        if not country_ids or not country_ids[0]:
            return False
        _logger.debug("country [%s] found as [%s]", country, country_ids[0])
        return country_ids[0]

    def _pdsl_find_state_id(self, cr, uid, state, country_id, context=None):
        """Return the appropriate state_id. """
        query = [('code', 'ilike', state), ('country_id', '=', country_id)]
        state_pool = self.pool.get('res.country.state')
        state_ids = state_pool.search(cr, uid, query, limit=1, context=context)
        if not state_ids or not state_ids[0]:
            return False
        _logger.debug("state [%s] found as [%s]", state, state_ids[0])
        return state_ids[0]

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """
        Override this mail.thread method in order to fill more data in Leads.
        """
        defaults = {}
        if custom_values is None:
            custom_values = {}
        if context is None:
            context = {}

        def set_country(val):
            country_id = self._pdsl_find_country_id(
                cr, uid, country=val, context=context)
            if country_id:
                defaults['country_id'] = country_id
            if country_id and context.get('pdsl_state'):
                state = context.get('pdsl_state')
                state_id = self._pdsl_find_state_id(
                    cr, uid, state=state, country_id=country_id,
                    context=context)
                if state_id:
                    defaults['state_id'] = state_id

        def set_state(val):
            if not defaults.get('country_id', None):
                context['pdsl_state'] = val
                return
            state_id = self._pdsl_find_state_id(
                cr, uid, state=val, country_id=defaults['country_id'],
                context=context)
            if state_id:
                defaults['state_id'] = state_id

        def set_categ(val):
            new_tag_id = self._pdsl_find_categ(
                cr, uid, action=val, context=context)
            if new_tag_id:
                # Get existing tags
                tags_ids = defaults.get('categ_ids', [(6, 0, [])])[0][2]
                # Append ours.
                tags_ids.append(new_tag_id)
                defaults['categ_ids'] = [(6, 0, tags_ids)]

        # Read data contains in email. If no special data, just create a plain
        # Leads using default implementation.
        maps = {
            'name': 'contact_name',
            'phone': 'phone',
            'street': 'street',
            'street2': 'street2',
            'city': 'city',
            'state': set_state,
            'country': set_country,
            'zip': 'zip',
            'action': set_categ,
            'product': lambda val: map(set_categ, val.split(' ')),
        }
        for key in maps:
            if key in msg:
                if hasattr(maps[key], '__call__'):
                    maps[key](msg[key])
                else:
                    defaults[maps[key]] = msg[key]

        # Try to assign a default sales team.
        section_id = False
        try:
            section_id = self.pool.get('ir.model.data').get_object_reference(
                cr, uid, 'crm', "section_sales_department")[1]
        except:
            pass
        if not section_id:
            section_id = self.pool.get('crm.case.section').search(
                cr, uid, [], limit=1, context=context)[0]
        defaults['section_id'] = section_id

        # Keep reference to the original message (for confirmation).
        body = tools.html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults['description'] = body

        # Create the lead
        defaults.update(custom_values)
        return super(crm_lead, self).message_new(
            cr, uid, msg, custom_values=defaults, context=context)

    def message_post(self, cr, uid, thread_id, body='', subject=None,
                     type='notification', subtype=None, parent_id=False,
                     attachments=None, context=None,
                     content_subtype='html', **kwargs):
        """
        Implementation to trigger workflow by updating the lead every time a
        message is posted. This should happen right after the creation of the
        lead.
        """

        if context is None:
            context = {}

        res = super(crm_lead, self).message_post(
            cr, uid, thread_id, body=body, subject=subject, type=type,
            subtype=subtype, parent_id=parent_id, attachments=attachments,
            context=context, content_subtype=content_subtype, **kwargs)

        if thread_id:
            self.write(cr, uid, thread_id, {'date_action_last': time.strftime(
                tools.DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)

        return res

    def message_update(self, cr, uid, ids, msg, update_vals=None,
                       context=None):

        if update_vals is None:
            update_vals = {}
        if context is None:
            context = {}

        def set_categ(val):
            tag_id = self._pdsl_find_categ(
                cr, uid, action=val, context=context)
            if tag_id:
                update_vals['categ_ids'] = [(4, tag_id)]

        # Read data contains in email. If no special data, just create a
        # plain Leads using default implementation.
        body = tools.html2plaintext(msg.get('body')) if msg.get('body') else ''
        maps = {
            'action': set_categ,
        }
        for line in body.split('\n'):
            line = line.strip()
            m = pdsl_command_re.match(line)
            if m and maps.get(m.group(1).lower()):
                key = maps.get(m.group(1).lower())
                value = m.group(2)
                if hasattr(key, '__call__'):
                    key(value)
                else:
                    update_vals[key] = value

        return super(crm_lead, self).message_update(
            cr, uid, ids, msg, update_vals=update_vals, context=context)


class project_issue(models.Model):
    _name = 'project.issue'
    _inherit = 'project.issue'

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------

    def _pdsl_find_categ(self, cr, uid, action, context=None):
        """Search categories related to the mail."""
        tags_pool = self.pool.get('project.category')
        tag_ids = tags_pool.search(
            cr, uid, [('name', 'ilike', action)], limit=1, context=context)
        if not tag_ids or not tag_ids[0]:
            return False
        _logger.debug(
            "action [%s] found as category [] categories [%s]",
            action, tag_ids[0])
        return tag_ids[0]

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """
        Override this mail.thread method in order to sets categories.
        Uses the action and product fields to set the category.
        """
        defaults = {}
        if custom_values is None:
            custom_values = {}
        if context is None:
            context = {}

        # Set reasonable category value using action and product.
        tag_ids = []
        tag_names = [msg.get('action', None), msg.get('product', None)]
        for tag_name in tag_names:
            tag_id = self._pdsl_find_categ(cr, uid, tag_name, context=context)
            if tag_id:
                tag_ids.append(tag_id)
        if tag_ids:
            defaults['categ_ids'] = [(6, 0, tag_ids)]

        # Keep reference to the original message (for confirmation).
        body = tools.html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults['description'] = body

        # Create the issue
        defaults.update(custom_values)
        return super(project_issue, self).message_new(
            cr, uid, msg, custom_values=defaults, context=context)
