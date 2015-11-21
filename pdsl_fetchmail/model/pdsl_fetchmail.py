# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL fetchmail addons
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
import logging
import re
import time

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from openerp import tools
from openerp import models
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

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
            (key, sep, value) = line.partition(': ')
            data[key] = value
        elif data.get('message'):
            data['message'] += line
        else:
            data['message'] = line
    
    return data


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
        tag_ids = tags_pool.search(cr, uid, [('name', 'ilike', action)], limit=1, context=context)
        if not tag_ids or not tag_ids[0]:
            return False
        _logger.debug("action [%s] found as category []categories [%s]", action, tag_ids[0])
        return tag_ids[0]
    
    def _pdsl_find_country_id(self, cr, uid, country, context=None):
        """ Return the appropriate country_id. """
        country_pool = self.pool.get('res.country')
        country_ids = country_pool.search(cr, uid, [('code', 'ilike', country)], limit=1, context=context)
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
    
    def _pdsl_find_lang(self, cr, uid, lang, context=None):
        """Search the language code in all available language."""
        pool_lang = self.pool.get('res.lang')
        lang_ids = pool_lang.search(cr, uid, [('code', 'ilike', lang)], limit=1, context=context)
        if not lang_ids or not lang_ids[0]:
            return False
        lang_obj = pool_lang.browse(cr, uid, lang_ids[0], context=context)
        _logger.debug('language [%s] found as [%s]', lang, lang_obj.code)
        return lang_obj.code
    
    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """
        Override this mail.thread method in order to fill more data in Leads.
        """
        defaults = {}
        if custom_values is None:
            custom_values = {}
        if context is None:
            context = {}
        
        def set_lang_context(val):
            lang_code = self._pdsl_find_lang(cr, uid, lang=val, context=context)
            if lang_code:
                context['lang'] = lang_code
        
        def set_country(val):
            country_id = self._pdsl_find_country_id(cr, uid, country=val, context=context)
            if country_id:
                defaults['country_id'] = country_id 
            if country_id and context.get('pdsl_state'):
                state = context.get('pdsl_state')
                state_id = self._pdsl_find_state_id(
                    cr, uid, state=state, country_id=country_id, context=context)
                if state_id:
                    defaults['state_id'] = state_id

        def set_state(val):
            if not defaults['country_id']:
                context['pdsl_state'] = val
                return
            state_id = self._pdsl_find_state_id(
                cr, uid, state=val, country_id=defaults['country_id'], context=context)
            if state_id:
                defaults['state_id'] = state_id
        
        def set_categ(val):
            tag_id = self._pdsl_find_categ(cr, uid, action=val, context=context)
            if tag_id:
                defaults['categ_ids'] = [(6, 0, [tag_id,])] 
            
        def set_from(val):
            defaults['email_from'] = val
            # Replace original from value.
            partner_obj = self.pool.get('res.partner')
            author_ids = partner_obj.search(cr, uid, [('email', 'ilike', val)], limit=1, context=context)
            if author_ids:
                msg['author_id'] = author_ids[0]
        
        # Read data contains in email. If no special data, just create a plain Leads
        # using default implementation.
        body = tools.html2plaintext(msg.get('body')) if msg.get('body') else ''
        maps = {
            'name': 'contact_name',
            'email': set_from,
            'phone': 'phone',
            'street':'street',
            'street2':'street2',
            'city':'city',
            'state': set_state,
            'country': set_country,
            'zip': 'zip',
            'lang': set_lang_context,
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
                    defaults[key] = value
        
        # Try to assign a default sales team.
        try:
            defaults['section_id'] = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm', "section_sales_department")[1]
        except:
            pass
        
        # Create the issue
        defaults.update(custom_values)
        return super(crm_lead, self).message_new(
            cr, uid, msg, custom_values=defaults, context=context)
        
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                        subtype=None, parent_id=False, attachments=None, context=None,
                        content_subtype='html', **kwargs):
        """
        Implementation to trigger workflow by updating the lead every time a
        message is posted. This should happen right after the creation of the
        lead.
        """
        
        if context is None:
            context = {}
        
        res = super(crm_lead, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, content_subtype=content_subtype, **kwargs)
        
        if thread_id:
            self.write(cr, uid, thread_id, {'date_action_last': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)    
        
        return res
        
    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        
        if update_vals is None:
            update_vals = {}
        if context is None:
            context = {}
            
        def set_categ(val):
            tag_id = self._pdsl_find_categ(cr, uid, action=val, context=context)
            if tag_id:
                update_vals['categ_ids'] = [(4, tag_id)] 
            
        # Read data contains in email. If no special data, just create a plain Leads
        # using default implementation.
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

        return super(crm_lead, self).message_update(cr, uid, ids, msg, update_vals=update_vals, context=context)
        
        
    # ----------------------------------------
    # Workflow
    # ----------------------------------------
        
    def pdsl_new(self, cr, uid, ids, context=None):
        _logger.debug('workflow starting!')
        
    def pdsl_stop(self, cr, uid, ids, context=None):
        _logger.debug('workflow stop!')
        
    def pdsl_is_category(self, cr, uid, ids, context=None, category=None):
        """
        Check if the given issue is tag with given category.
        """  
        # Compare the result with the issue tags.
        issue = self.pool.get('crm.lead').browse(cr, uid, ids[0], context=context)
        if not issue or not issue.categ_ids:
            return False

        for tag in issue.categ_ids:
            if tag.name.lower() == category.lower():
                return True

        return False
    
    def pdsl_is_subscribe(self, cr, uid, ids, context=None):
        """
        Check if the issue is a subscription request.
        Return true if subscription request.
        """
        return self.pdsl_is_category(cr, uid, ids, context=context, category='subscribe')

    def pdsl_is_confirmed(self, cr, uid, ids, context=None):
        """
        Check if the issue is a subscription request.
        Return true if subscription request.
        """
        return self.pdsl_is_category(cr, uid, ids, context=context, category='confirm')
    
    def pdsl_is_support(self, cr, uid, ids, context=None):
        """
        Check if the issue is a subscription request.
        Return true if subscription request.
        """
        return self.pdsl_is_category(cr, uid, ids, context=context, category='support')
    
    
    def pdsl_send_confirm(self, cr, uid, ids, context=None, subscription=False):
        """
        Called by workflow to send confirmation message. Send an appropriate
        confirmation message.
        """
        
        # Try to determine the best language to be used.
        if context is None:
            context = {}
        # context['lang'] = self._pdsl_get_context_lang(cr, uid, ids[0], context)
        
        # Check if the current issue is a "subscription request".
        # If so, send a confirmation to verify his EMAIL.
        if subscription:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', 'pdsl_fetchmail_subscription_confirm_email_template')[1]
        else:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', 'pdsl_fetchmail_support_confirm_email_template')[1]
        
        # Send the mail
        _logger.info("sending confirmation mail")
        values = self.pool.get('email.template').generate_email(cr, uid, template_id, ids[0], context=context)
        self.pool.get('email.template').send_mail(cr, uid, template_id, ids[0], force_send=True, context=context)

        # Add a log to the issue about confirmation being sent.
        super(crm_lead, self).message_post(
            cr, uid, ids[0], subject=values['subject'], body=values['body'], type='email', context=context)
