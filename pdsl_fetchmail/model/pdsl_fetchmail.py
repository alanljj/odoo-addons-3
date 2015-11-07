# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL fetchmail addons
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
import logging
import re

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from openerp.osv import orm
from openerp.tools import html2plaintext
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


class crm_lead(orm.Model):
    """
    Enhance reception of mail to create CRM Lead with more data.
    """
    _name = 'crm.lead'
    _inherit = 'crm.lead'
    
    def _pdsl_find_categ(self, cr, uid, action, context=None):
        """Search categories related to the mail."""
        tags_pool = self.pool.get('crm.case.categ')
        tag_ids = tags_pool.search(cr, uid, [('name', 'ilike', action)], limit=1, context=context)
        _logger.debug("categories id %s found for [%s]", tag_ids, action)
        return [(6, 0, tag_ids)]
    
    def _pdsl_find_country_id(self, cr, uid, country, context=None):
        """ Return the appropriate country_id. """
        _logger.debug("search for country [%s]", country)
        country_pool = self.pool.get('res.country')
        country_ids = country_pool.search(cr, uid, [('code', 'ilike', country)], limit=1, context=context)
        if not country_ids or not country_ids[0]:
            return False
        return country_ids[0]
    
    def _pdsl_find_lang(self, cr, uid, lang, context=None):
        """Search the language code in all available language."""
        pool_lang = self.pool.get('res.lang')
        lang_ids = pool_lang.search(cr, uid, [('code', 'ilike', lang)], limit=1, context=context)
        if lang_ids:
            lang_obj = pool_lang.browse(cr, uid, lang_ids[0], context=context)
            _logger.debug('language code [%s] found for [%s]', lang_obj.code, lang)
            return lang_obj.code
        return False
    
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
            context['lang'] = self._pdsl_find_lang(cr, uid, lang=val, context=context)
        
        def set_country(val):
            defaults['country_id'] = self._pdsl_find_country_id(cr, uid, country=val, context=context)
        
        def set_categ(val):
            defaults['categ_ids'] = self._pdsl_find_country_id(cr, uid, action=val, context=context)
        
        # Read data contains in email. If no special data, just create a plain Leads
        # using default implementation.
        body = html2plaintext(msg.get('body')) if msg.get('body') else ''
        maps = {
            'name': 'contact_name',
            'email': 'email',
            'phone': 'phone',
            'street':'street',
            'street2':'street2',
            'city':'city',
            'state':'state',
            'country': set_country,
            'zip': 'zip',
            'lang': set_lang_context,
            'action': set_categ,
        }
        for line in body.split('\n'):
            line = line.strip()
            res = pdsl_command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                value = res.group(2)
                if hasattr(key, '__call__'):
                    key(value)
                else:
                    defaults[key] = value
        
        # Create the issue
        defaults.update(custom_values)
        return super(crm_lead, self).message_new(
            cr, uid, msg, custom_values=defaults, context=context)
    

class project_issue(orm.Model):
    _name = 'project.issue'
    _inherit = 'project.issue'

    def _pdsl_get_context_lang(self, cr, uid, issue_id=None, context=None, data_dict=False):
        """ From the message content, determine the appropriate language.
            Either French of English. If the message doesn't provide a valid
            language, default to context. If not available, default to current
            user id language."""

        # Get language from issue
        if issue_id:
            issue = self.pool.get('project.issue').browse(cr, uid, issue_id, context=context)
            if issue and issue.description:
                data_dict = _parse_body(issue.description)
        
        # Search the language code in all available language.
        if data_dict and data_dict.get('lang'):
            lang = data_dict.get('lang')
            pool_lang = self.pool.get('res.lang')
            lang_ids = pool_lang.search(cr, uid, [('code', 'ilike', lang)], limit=1, context=context)
            if lang_ids:
                lang_obj = pool_lang.browse(cr, uid, lang_ids[0], context=context)
                _logger.info('language found [%s]' % (lang_obj.code,))
                return lang_obj.code
        
        # Get the current user language.
        users_pool = self.pool.get('res.users')
        user = users_pool.browse(cr, uid, uid, context=context)
        return user.partner_id.lang
    
    def _issue_get_default_assign_to_user_id(self, cr, uid, data_dict, context):
        """ Find a user to be assigned to the issue. """
        # Get reference to the project
        project_id = self._issue_get_default_project_id(cr, uid, data_dict, context=context)
        if not project_id:
            return False
        # Use the project manager as user_id
        _logger.debug('search user_id for project_id [%s]' % project_id)
        project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
        if project and project.user_id:
            _logger.debug('user_id found [%s]' % project.user_id.id)
            return project.user_id.id
        return False
        
    def _issue_get_default_color(self, cr, uid, data_dict, context):
        """ Return the default color from color project. """
        project_id = self._issue_get_default_project_id(cr, uid, data_dict, context=context)
        if not project_id:
            return False
        # Use the project manager as user_id
        _logger.debug('search for project_id [%s]' % project_id)
        project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
        if project and project.color:
            _logger.debug('color found [%s]' % project.color)
            return project.color
        return False
        
    def _issue_get_default_description(self, cr, uid, data_dict, context):
        """ Create a pretty Json to be reused for further processing! It's
            the only way I found to store extra data. """
        # Format data.
        return _format_body(data_dict, filterout=['email', 'subject', 'action'])
        
    def _issue_get_default_name(self, cr, uid, data_dict, context):
        """ Create a proper subject name for the incident. """
        name = ""
        if data_dict.get('product'):
            name += data_dict['product'] + ": "
        if data_dict.get('subject'):
            name += data_dict['subject']
        elif data_dict.get('action'):
            name += data_dict['action']
        return name
    
    def _issue_get_default_project_id(self, cr, uid, data_dict, context):
        """ Search for an appropriate project related to the mail. """
        
        project_pool = self.pool.get('project.project')
        project_ids = []
        
        # product contains a list of the product
        if data_dict.get('product'):
            product_desc = data_dict.get('product')
            for desc in product_desc.split(' '): 
                _logger.debug("search for project [%s]", desc)
                project_ids += project_pool.search(cr, uid, [('name', 'ilike', desc)], limit=1, context=context)
            # Check return and return the value if found
            if len(project_ids) > 0:
                _logger.debug("projects found [%s]", project_ids)
                return project_ids[0]
        
        # try to find one with action
        if data_dict.get('action'):
            desc = data_dict.get('action')
            _logger.debug("search for project [%s]", desc)
            project_ids += project_pool.search(cr, uid, [('name', 'ilike', desc)], limit=1, context=context)
            # Check return and return the value if found
            if len(project_ids) > 0:
                _logger.debug("projects found %s", project_ids)
                return project_ids[0]
            
            
        # try to use the default project.
        try:
            return self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', "project_project_pdsl_default")[1]
        except:
            _logger.info("project not found!")
        return False
    
    def _issue_get_default_partner_id(self, cr, uid, data_dict, context):
        """ Find partners related to some header fields of the message. """
        
        if not data_dict or not data_dict.get('email'):
            return False
        
        partner_obj = self.pool.get('res.partner')
        partner_id = False
        partner_ids = []
        related_partners = partner_obj.search(cr, uid, [('email', 'ilike', data_dict.get('email')), ('user_ids', '!=', False)], limit=1, context=context)
        if not related_partners:
            related_partners = partner_obj.search(cr, uid, [('email', 'ilike', data_dict.get('email'))], limit=1, context=context)
        partner_ids += related_partners
        # Return the first partner id matching.
        if partner_ids:
            partner_id = partner_ids[0]
            _logger.info("partner_id found %s", partner_id)
        return partner_id
    
    def _issue_get_default_stage_id(self, cr, uid, data_dict, context):
        """ Gives default stage_id """
        project_id = self._issue_get_default_project_id(cr, uid, data_dict, context)
        if not project_id:
            return False
        return super(project_issue, self).stage_find(cr, uid, [], project_id, [('state', '=', 'draft')], context=context)
    
    def _issue_get_default_tag_ids(self, cr, uid, data_dict, issue_id=False, context=None):
        """ Search tags related to the mail. """
        
        tag_ids = []
        tags_pool = self.pool.get('project.category')
        
        # If ids is given, fetch the current tags.
        if issue_id:
            issue = self.pool.get('project.issue').browse(cr, uid, issue_id, context=context)
            for tag in issue.categ_ids:
                tag_ids += [tag.id]
        
        # Search tags related to action.
        if data_dict.get('action'):
            desc = data_dict.get('action')
            _logger.info("search for tag [%s]", desc)
            tag_ids += tags_pool.search(cr, uid, [('name', 'ilike', desc)], limit=1, context=context)
        
        # product contains a list of the product
        if data_dict.get('product'):
            product_desc = data_dict.get('product')
            for desc in product_desc.split(' '): 
                _logger.info("search for tag [%s]", desc)
                tag_ids += tags_pool.search(cr, uid, [('name', 'ilike', desc)], limit=1, context=context)
        
        tag_ids = list(set(tag_ids))
        _logger.info("tags found %s", tag_ids)
        return [(6, 0, tag_ids)]
    
    def message_new(
        self, cr, uid, msg_dict, custom_values=None, context=None):
        """
        Override this mail.thread method in order to compose a set of
        valid values for the contract and partner to be created. Current
        implementation expect some kind of python data in email.
        """       
        
        # Create a default custom values dict.
        defaults = {}
        if custom_values is None:
            custom_values = {}
        
        # As the scheduler is run without language,
        # set the administrator's language by default
        if context is None:
            context = {}
        context['lang'] = self._pdsl_get_context_lang(cr, uid, context=context)
        
        # Read data contains in email. If no special data, just create a plain task
        # using default implementation.
        body = html2plaintext(msg_dict.get('body'))
        data_dict = _parse_body(body)
        if data_dict:
            _logger.info("formated message received!")
            context['lang'] = self._pdsl_get_context_lang(cr, uid, context=context, data_dict=data_dict)
            # Calling this method will change the custom_values
            defaults = {
                'project_id': self._issue_get_default_project_id(cr, uid, data_dict, context=context),
                'stage_id' : self._issue_get_default_stage_id(cr, uid, data_dict, context=context),
                'partner_id': self._issue_get_default_partner_id(cr, uid, data_dict, context=context),
                'name' : self._issue_get_default_name(cr, uid, data_dict, context=context),
                'description': self._issue_get_default_description(cr, uid, data_dict, context=context),
                'user_id': self._issue_get_default_assign_to_user_id(cr, uid, data_dict, context=context),
                'email_from': data_dict.get('email'),
                'categ_ids': self._issue_get_default_tag_ids(cr, uid, data_dict, context=context),
                'color' : self._issue_get_default_color(cr, uid, data_dict, context=context),
                'message_follower_ids' : False
            }
        
        # Create the issue
        defaults.update(custom_values)
        return super(project_issue, self).message_new(
            cr, uid, msg_dict, custom_values=defaults, context=context)

    def message_route(self, cr, uid, message, model=None, thread_id=None,
                      custom_values=None, context=None):
        
        return super(project_issue, self).message_route(cr, uid, message, model=model, thread_id=thread_id, custom_values=custom_values, context=context)
        

    def message_update(self, cr, uid, ids, msg_dict, update_vals=None, context=None):
        """ Called when receiving a new message with 'Reply-To' (for an existing thread_id). """
        
        _logger.info("message received !")
        
        # Create a default custom values dict.
        if update_vals is None:
            update_vals = {}
            
        # As the scheduler is run without language,
        # set the administrator's language by default
        if context is None:
            context = {}
            
        # Read data contains in email. If no special data, just create a plain task
        # using default implementation.
        body = html2plaintext(msg_dict.get('body')) 
        data_dict = _parse_body(body)
        # Check if the mail is a confirm message.
        if data_dict and data_dict.get('action') and data_dict['action'] == 'confirm':
            _logger.info("formated message received!")
            context['lang'] = self._pdsl_get_context_lang(cr, uid, data_dict, context=context)
            # Add a confirm tags.
            update_vals = {
                'categ_ids': self._issue_get_default_tag_ids(cr, uid, data_dict, issue_id=ids[0], context=context)
            }
        
        # Update the issue fields.
        return super(project_issue, self).message_update(cr, uid, ids, msg_dict, update_vals, context=context)

    def _partner_get_default_state_id(self, cr, uid, data_dict, context=None):
        """ Return the appropriate state_id. """
        # Get reference to country_id
        country_id = self._partner_get_default_country_id(cr, uid, data_dict, context=context)
        if not country_id or not data_dict.get('state'):
            return False
        
        # Search the state.
        query = [
            ('code', 'ilike', data_dict['state']),
            ('country_id', '=', country_id)]
        state_pool = self.pool.get('res.country.state')
        state_ids = state_pool.search(cr, uid, query, limit=1, context=context)
        if not state_ids or not state_ids[0]:
            return False
        
        return state_ids[0]
        
    def _partner_get_default_country_id(self, cr, uid, data_dict, context=None):
        """ Return the appropriate country_id. """
        # Return false if the required fields are not define.
        if not data_dict or not data_dict.get('country'):
            return False
        # Search for the country code.
        _logger.info("search for country [%s]" % (data_dict['country']))
        country_pool = self.pool.get('res.country')
        country_ids = country_pool.search(cr, uid, [('code', 'ilike', data_dict['country'])], limit=1, context=context)
        if not country_ids or not country_ids[0]:
            return False
        return country_ids[0]
    
    def pdsl_create_partner(self, cr, uid, ids, context=None):
        """ Create a partner for the given issue_id. This issue must have a
            description containing the information to create the partner. """
        # If issue it not provided, we can't get reference to the data to
        # create the partner. So Skip creation! Should not happen!.
        for issue_id in ids:
            # Get reference to issue object.
            issue = self.pool.get('project.issue').browse(cr, uid, issue_id, context=context)
            if not issue or not issue.description:
                # This should not happen either.
                _logger.error("can't create partner for issue_id [%s]" % (issue_id))
                return False
            
            # Create partner entry
            data_dict = _parse_body(issue.description)
            partner_pool = self.pool.get('res.partner')
            partner_data = {
                'name': data_dict.get('name') or '',
                'email': data_dict.get('email'),
                'phone': data_dict.get('phone'),
                'street': data_dict.get('street'),
                'street2': data_dict.get('street2'),
                'city': data_dict.get('city'),
                'state_id': self._partner_get_default_state_id(cr, uid, data_dict, context=context),
                'country_id': self._partner_get_default_country_id(cr, uid, data_dict, context=context),
                'zip': data_dict.get('zip')
            }
            _logger.info("creating new partner [%s]", data_dict.get('email'))
            partner_id = partner_pool.create(cr, uid, partner_data, context=context)
            
            # Assign pattern to the issue.
            self.write(cr, uid, ids, {'partner_id': partner_id})
    
    def pdsl_create_user(self, cr, uid, ids, context):
        """
        Used to create the user in LDAP.
        """
        _logger.info("creating new user in Minarca")
        return True
    
    def pdsl_is_category(self, cr, uid, issue_id, context=None, category=None):
        """
        Check if the given issue is tag with given category.
        """  
        # Compare the result with the issue tags.
        issue = self.pool.get('project.issue').browse(cr, uid, issue_id, context=context)
        if not issue or not issue.categ_ids:
            return False

        for tag in issue.categ_ids:
            if tag.name == category:
                return True

        return False
    
    def pdsl_is_subscription(self, cr, uid, ids, context=None):
        """
        Check if the issue is a subscription request.
        Return true if subscription request.
        """
        return self.pdsl_is_category(cr, uid, ids[0], context=context, category='subscribe')

    def pdsl_is_confirmed(self, cr, uid, ids, context=None):
        """
        Check if the issue is a subscription request.
        Return true if subscription request.
        """
        return self.pdsl_is_category(cr, uid, ids[0], context=context, category='confirm')
    
    def pdsl_is_support(self, cr, uid, ids, context=None):
        """
        Check if the issue is a subscription request.
        Return true if subscription request.
        """
        return self.pdsl_is_category(cr, uid, ids[0], context=context, category='support')
    
    def pdsl_new_issue(self, cr, uid, ids, context=None):
        """
        Function called by the workflow when a new issue is created.
        """
        _logger.info("new issue was created")
        # Search our custom state for "Open"
        stage_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', 'project_tt_new')[1]
        if not stage_id:
            return
        # Update the issue with Open State !
        self.write(cr, uid, ids, {'stage_id': stage_id})
    
    def pdsl_open(self, cr, uid, ids, context=None):
        """
        Called by the workflow when issue should be open.
        This function change the issue state to "open".
        """
        _logger.info("issue open")
        # Search our custom state for "Open"
        stage_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', 'project_tt_open')[1]
        if not stage_id:
            return
        # Update the issue with Open State !
        self.write(cr, uid, ids, {'stage_id': stage_id})
    
    def pdsl_send_confirm(self, cr, uid, ids, context=None, subscription=False):
        """
        Called by workflow to send confirmation message. Send an appropriate
        confirmation message.
        """
        
        # Try to determine the best language to be used.
        if context is None:
            context = {}
        context['lang'] = self._pdsl_get_context_lang(cr, uid, ids[0], context)
        
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
        super(project_issue, self).message_post(cr, uid, ids[0],
                                                subject=values['subject'],
                                                body=values['body'],
                                                type='email',
                                                context=context)
        
    
    
