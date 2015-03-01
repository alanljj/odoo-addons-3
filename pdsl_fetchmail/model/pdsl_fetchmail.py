# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL fetchmail addons
# Copyright (C) 2014 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################
import logging

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from openerp.osv import orm
from openerp.tools import html2plaintext
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class project_issue(orm.Model):
    _name = 'project.issue'
    _inherit = 'project.issue'

    def create(self, cr, uid, vals, context=None):
        """ When creating a new issue. Send confirmation mail."""
        # Create the object.
        new_id = super(project_issue, self).create(cr, uid, vals, context=context)
        
        _logger.info("COUCOU")
        issue = self.pool.get('project.issue').browse(cr, uid, new_id, context=context)
        _logger.info(issue.message_follower_ids)
        
        # Then send confirmation message.
        if context and context.get('pdsl_send_confirmation'):
            # Once the Task is created, send a confirmation message to the partner.
            self._issue_send_confirm(cr, uid, new_id, context=context)
        
        return new_id

    def _is_subscribe(self, cr, uid, issue_id, context):
        """Check if the issue is a subscription request. Return true if subscription request."""
        
        # This implementation check if the issue is tag with "subscribe". 
        try:
            tag_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', 'project_category_subscribe')[1]
        except:
            return False
        
        # Compare the result with the issue tags.
        issue = self.pool.get('project.issue').browse(cr, uid, issue_id, context=context)
        if issue and issue.categ_ids:
            for tag in issue.categ_ids:
                if(tag.id == tag_id):
                    return True
                
        return False

    def _create_partner(self, cr, uid, issue_id, context=None):
        """ Create a partner for the given issue_id. This issue must have a
            description containing the information to create the partner. """
        # If issue it not provided, we can't get reference to the data to
        # create the partner. So Skip creation! Should not happen!.
        if not issue_id:
            _logger.error("can't create partner for unknown issue_id")
            return False
        
        # Get reference to issue object.
        issue = self.pool.get('project.issue').browse(cr, uid, issue_id, context=context)
        if not issue or not issue.description:
            # This should not happen either.
            _logger.error("can't create partner for issue_id [%s]" % (issue))
            return False
        
        data_dict = self._issue_extract_data(issue.description)
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
        return partner_id
    
    def _issue_extract_data(self, value):
        """ Used to read the message body as json."""
        # If value is not a string, return false.
        if not value:
            return False
        
        try:
            # Try to convert the body as Json.
            desc = html2plaintext(value)
            return json.loads(desc)
        except:
            # Return false in case of error.
            return False
    
    def _issue_get_context_lang(self, cr, uid, data_dict=False, context=None):
        """ From the message content, determine the appropriate language.
            Either French of English. If the message doesn't provide a valid
            language, default to context. If not available, default to current
            user id language."""
        
        # Search the language code in all available language.
        if data_dict and data_dict.get('lang'):
            lang = data_dict.get('lang')
            pool_lang = self.pool.get('res.lang')
            lang_ids = pool_lang.search(cr, uid,[('code', 'ilike', lang)], limit=1, context=context)
            if lang_ids:
                lang_obj = pool_lang.browse(cr, uid, lang_ids[0], context=context)
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
        _logger.debug('search user_id for project_id [%s]' % project_id)
        project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
        if project and project.color:
            _logger.debug('color found [%s]' % project.color)
            return project.color
        return False
        
    def _issue_get_default_description(self, cr, uid, data_dict, context):
        """ Create a pretty Json to be reused for further processing! It's
            the only way I found to store extra data. """
        # Pretty print json
        return json.dumps(data_dict, indent=4, sort_keys=True)
        
        #desc = ""
        #for (key, value) in data_dict.iteritems():
        #    if key in ['message', 'subject', 'email', 'action']:
        #        continue
        #    if value and len(value) > 0:
        #        desc += "%s: %s\n" % (key, value)
        #if data_dict.get('message'):
        #    desc += "\n"
        #    desc += data_dict.get('message')
        #return desc
        
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
    
    def _issue_send_confirm(self, cr, uid, issue_id, context):
        """ Send an appropriate confirmation message. """
        
        # By default return a confirmation message for support
        template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', 'pdsl_fetchmail_support_confirm_email_template')[1]
        
        # If the message receive is explicitly related to a subscription, send a subscription confirmation message.
        if (self._is_subscribe(cr, uid, issue_id, context=context) and
                context['pdsl_confirmation_messageid']):
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pdsl_fetchmail', 'pdsl_fetchmail_subscription_confirm_email_template')[1]
        
        # Send the mail
        _logger.info("Sending confirmation mail")
        values = self.pool.get('email.template').generate_email(cr, uid, template_id, issue_id, context=context)
        self.pool.get('email.template').send_mail(cr, uid, template_id, issue_id, force_send=True, context=context)
            
        # Add a log to the issue about confirmation being sent.
        super(project_issue, self).message_post(cr, uid, issue_id,
                                                subject=values['subject'],
                                                body=values['body'],
                                                type='email',
                                                context=context)

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
        context['lang'] = self._issue_get_context_lang(cr, uid, context=context)
        
        # After creation, send a confirmation message
        context['pdsl_send_confirmation'] = True
        context['pdsl_confirmation_messageid'] = msg_dict['message_id']
        
        # Read data contains in email. If no special data, just create a plain task
        # using default implementation. 
        data_dict = self._issue_extract_data(msg_dict.get('body'))
        if data_dict:
            _logger.info("json message received!")
            context['lang'] = self._issue_get_context_lang(cr, uid, data_dict, context=context)
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
        data_dict = self._issue_extract_data(msg_dict.get('body'))
        # Check if the mail is a confirm message.
        if data_dict and data_dict.get('action') and data_dict['action'] == 'confirm':
            _logger.info("json message received!")
            context['lang'] = self._issue_get_context_lang(cr, uid, data_dict, context=context)
            # Add a confirm tags.
            update_vals = {
                'partner_id': self._create_partner(cr, uid, issue_id=ids[0], context=context),
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
