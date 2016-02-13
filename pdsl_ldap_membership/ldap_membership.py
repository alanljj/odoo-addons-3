# -*- coding: utf-8 -*-
##############################################################################
#
# PDSL Invoice
# Copyright(C) 2015 Patrik Dufresne Service Logiciel (http://www.patrikdufresne.com).
#
##############################################################################


import base64
import hashlib
from ldap import modlist 
import ldap
import logging
import os
import re
import string
import time

from openerp import api, models, _
from openerp.exceptions import Warning
from openerp.osv import fields
from openerp.osv import osv


_logger = logging.getLogger(__name__)


ACTIVE_STATES = ('paid', 'invoiced', 'free')


class Invoice(osv.Model):
    '''Invoice'''
    _inherit = 'account.invoice'
    
    # ----------------------------------------
    # Invoice state management vs membership
    # ----------------------------------------
    
    def invoice_validate(self, cr, uid, ids, context=None):
        """
        Override to update membership line.
        """
        # Call original implementation to update the invoice.
        res = super(Invoice, self).invoice_validate(cr, uid, ids, context=context)
        #
        member_line_obj = self.pool.get('membership.membership_line')
        for invoice in self.browse(cr, uid, ids, context=context):
            mlines = member_line_obj.search(cr, uid,
                    [('account_invoice_line', 'in',
                        [l.id for l in invoice.invoice_line])])
            if mlines:
                member_line_obj.write(cr, uid, mlines, {'date_cancel': None})
        return res        
    
    def action_cancel_draft(self, cr, uid, ids, context=None):
        """
        Override to update membership lines.
        """
        # Remove date_cancel.
        member_line_obj = self.pool.get('membership.membership_line')
        for invoice in self.browse(cr, uid, ids, context=context):
            mlines = member_line_obj.search(cr, uid,
                    [('account_invoice_line', 'in',
                        [l.id for l in invoice.invoice_line])])
            if mlines:
                member_line_obj.write(cr, uid, mlines, {'date_cancel': None})
        return super(Invoice, self).action_cancel_draft(cr, uid, ids, context=context)

    # ----------------------------------------
    # Invoice state management vs membership
    # ----------------------------------------

    @api.multi
    def _pdsl_check_ldap_membership_update_required(self, vals):
        """
        Determine if an update to LDAP membership is required.
        """
        if 'state' in vals:
            # TODO Check if the invoice contains any membership lines ?
            return True
        return False
        
    @api.multi
    def write(self, vals):
        res = super(Invoice, self).write(vals)
        # Check if ldap mem
        if self._pdsl_check_ldap_membership_update_required(vals):
            self.partner_id.pdsl_update_ldap_membership()
        return res

class ProductTemplate(osv.osv):
    """Add column to product"""
    _inherit = "product.template"
    _columns = {
        'ldap_membership_group': fields.char('Membership Group Name', size=64, required=False,
            help="Comma seperated list of group name to represent the product membership in LDAP."),
    }
    _defaults = {
        'ldap_membership_group': False,
    }
    
    @api.multi
    def pdsl_update_ldap_group(self):
        """
        Create LDAP group to represent the membership.
        Return True if an LDAP group was created.
        """
        if not self.ldap_membership_group:
            return

        _logger.info('updating LDAP product')
        
        # Connect to LDAP server
        ldap_obj = self.env['res.company.ldap']
        for conf in ldap_obj.get_ldap_dicts():
            try:
                l = ldap_obj.connect(conf)
                l.simple_bind_s(conf['ldap_binddn'], conf['ldap_password'].encode('utf-8'))
            except:
                l = conf = None
                _logger.warn('connection to LDAP server failed', exc_info=1)
        if not l:
            raise ValueError('LDAP execution failed')
        
        def _new_gid():
            """Query the ldap directory for a new gidNumber."""
            # Get list of uid. Pick Max +1
            r = l.search_s(
                base=conf['ldap_base'],
                scope=ldap.SCOPE_SUBTREE,
                filterstr='(&(objectClass=posixGroup)(gidNumber=*))',
                attrlist=['gidNumber'])
            if len(r) > 0:
                return max(int(u[1]['gidNumber'][0]) for u in r) + 1        
            raise ValueError("fail to find new gidNumber")
        
        changed = False
        try:
            for group_name in self.ldap_membership_group.split(','):
                # Remove extra space.
                group_name = group_name.strip(' ')
                # Build up expected group (should be bytes)
                group_name_b = group_name.encode('utf-8')
                attrs = {
                    'cn': group_name_b,
                }
                
                # Search group in LDAP.
                search_filter = ldap.filter.filter_format('(&(objectClass=posixGroup)(cn=%s))', (group_name_b,))
                r = l.search_s(
                    base=conf['ldap_base'],
                    scope=ldap.SCOPE_SUBTREE,
                    filterstr=search_filter,
                    attrlist=attrs.keys())
                if len(r) == 0:
                    # Define attributes that should never be changed.
                    attrs['description'] = self.name.encode('utf-8')
                    attrs['gidNumber'] = str(_new_gid())
                    attrs['objectclass'] = ['posixGroup']
                    
                    # User doesn't exists. Add it
                    dn = 'cn=%s,%s,%s' % (attrs['cn'], 'ou=Groups', conf['ldap_base'])
                    ldif = modlist.addModlist(attrs)
                    l.add_s(dn, ldif)
                    self.message_post(body=_("LDAP group %s created") % group_name) 
                    changed = True        
        finally:
            l.unbind_s()
            
        return changed
        
    
    @api.multi
    def write(self, vals):
        """Override to create the group in LDAP."""
        res = super(ProductTemplate, self).write(vals)
        # Check if ldap mem
        if any(f in vals for f in ['ldap_membership_group', 'name']):
            changed = self.pdsl_update_ldap_group()
            if changed:
                # TODO Should update all membership if ldap_membership_group change.
                pass
        return res
    

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    # Declare new fields.
    _columns = {
        'ldap_membership_login': fields.char('Membership Login', size=64, required=False,
            help="Used as username in LDAP to represent the partner"),
    }
    _defaults = {
        'ldap_membership_login': False,
    }

    @api.multi
    def _pdsl_set_ldap_user(self):
        """
        Call to create a new user in LDAP. Search for a free and
        available username.
        """
        # Connect to LDAP server
        ldap_obj = self.env['res.company.ldap']
        for conf in ldap_obj.get_ldap_dicts():
            try:
                l = ldap_obj.connect(conf)
                l.simple_bind_s(conf['ldap_binddn'], conf['ldap_password'].encode('utf-8'))
            except:
                l = conf = None
                _logger.warn('connection to LDAP server failed', exc_info=1)
        if not l:
            raise Warning('Fail to establish connection to LDAP server!')

        def _norm_username(username):
            """Remove or replace invalid char from username."""
            # Replace some char
            username = re.sub('[ \-]', '.', username.lower())
            # Remove invalid char
            return re.sub('[^a-z0-9.]', '', username)
        
        def _new_username():
            """Generate a unused ldap username."""
            candidates = []
            if self.name:
                candidates.append(_norm_username(self.name))
            if self.email and len(self.email.partition('@')[0]) > 8:
                candidates.append(_norm_username(self.email.partition('@')[0]))
            # Check if one is available.
            for c in candidates:
                search_filter = ldap.filter.filter_format(conf['ldap_filter'], (c.encode('utf-8'),))
                r = l.search_s(
                    base=conf['ldap_base'],
                    scope=ldap.SCOPE_SUBTREE,
                    filterstr=search_filter,
                    attrsonly=1)
                if len(r) == 0:
                    return c
            raise ValueError('cannot generate a unique username')           
        
        # Find a free user name.
        login = None
        try:
            login = _new_username()
        finally:
            l.unbind_s()
        
        # Update the user with this new user name.
        if login:
            self.write(vals={'ldap_membership_login': login})

    @api.multi
    def pdsl_update_ldap_membership(self):
        """
        Update or create the user in LDAP.
        """
        # Check if update is required.
        active = any(line.state in ACTIVE_STATES for line in self.member_lines)
        if not active and not self.ldap_membership_login:
            # Update not required.
            return
        
        # Generate a new username.
        if not self.ldap_membership_login:
            self._pdsl_set_ldap_user()

        _logger.info('updating user membership')
        
        # Connect to LDAP server
        ldap_obj = self.env['res.company.ldap']
        for conf in ldap_obj.get_ldap_dicts():
            try:
                l = ldap_obj.connect(conf)
                l.simple_bind_s(conf['ldap_binddn'], conf['ldap_password'].encode('utf-8'))
            except:
                l = conf = None
                _logger.warn('connection to LDAP server failed', exc_info=1)
        if not l:
            raise ValueError('LDAP execution failed')

        try:
            # Determine expiration date
            expire_date = int(time.time())
            # TODO Pick the date only if PAID. Otherwise, pick Date_From + 60 jours.
            end_dates = [time.mktime(time.strptime(line.date_to, '%Y-%m-%d'))
                         for line in self.member_lines
                         if line.state in ACTIVE_STATES]
            if end_dates:
                expire_date = int(max(end_dates))

            # Build list of description. One line per membership.
            groups = [line.membership_id.ldap_membership_group.split(',')
                for line in self.member_lines
                if line.state in ACTIVE_STATES
                if line.membership_id.ldap_membership_group]
            groups = set(item.strip(' ') for sublist in groups for item in sublist)
            groups_b = [g.encode('utf-8') for g in groups]

            # Build up expected user (should be bytes)
            ldap_membership_login_b = self.ldap_membership_login.encode('utf-8')
            attrs = {
                'shadowExpire': str(expire_date / 86400),  # / 24 / 60 / 60
                'description': groups_b,
            }
            
            # Search user in LDAP.
            search_filter = ldap.filter.filter_format(conf['ldap_filter'], (ldap_membership_login_b,))
            r = l.search_s(
                base=conf['ldap_base'],
                scope=ldap.SCOPE_SUBTREE,
                filterstr=search_filter,
                attrlist=attrs.keys())
            if len(r) == 0:
                # Raise exception user should exists.
                # Most likely user was deleted manually in LDAP.
                raise Warning("Ldap user %s doesn't exists!" % self.ldap_membership_login)
            
            # Update the record.
            dn = r[0][0]
            old = r[0][1]
            if attrs != old:
                ldif = modlist.modifyModlist(old, attrs)
                l.modify_s(dn, ldif)
            

            # Add user to each group
            for group_name in groups:
                group_name_b = group_name.encode('utf-8')
                # Search group
                search_filter = ldap.filter.filter_format('(&(objectClass=posixGroup)(cn=%s))', (group_name_b,))
                r = l.search_s(
                    base=conf['ldap_base'],
                    scope=ldap.SCOPE_SUBTREE,
                    filterstr=search_filter,
                    attrlist=['memberUid'])
                if len(r) == 0:
                    raise Warning("Ldap group %s doesn't exists!" % group_name)
                dn = r[0][0]
                old = r[0][1]
                if ldap_membership_login_b not in old.get('memberUid', []):
                    new = {'memberUid': list(old.get('memberUid', []))}
                    new['memberUid'].append(ldap_membership_login_b)
                    ldif = modlist.modifyModlist(old, new)
                    l.modify_s(dn, ldif)
            
            # TODO Remove user from other groups ?
            
            # Log this as an event.
            self.message_post(body=_("LDAP user membership updated"))
        finally:
            # Close connection
            l.unbind_s()

    @api.multi
    def pdsl_reset_password(self):
        """Reset user password."""
        self.pdsl_update_ldap_user(force_reset_password=True)

    @api.multi
    def pdsl_update_ldap_user(self, force_reset_password=False):
        """Update or create the LDAP user."""
        
        if not self.ldap_membership_login:
            return
        
        _logger.info('updating LDAP user')
        
        # Connect to LDAP server
        ldap_obj = self.env['res.company.ldap']
        for conf in ldap_obj.get_ldap_dicts():
            try:
                l = ldap_obj.connect(conf)
                l.simple_bind_s(conf['ldap_binddn'], conf['ldap_password'].encode('utf-8'))
            except:
                l = conf = None
                _logger.warn('connection to LDAP server failed', exc_info=1)
        if not l:
            raise ValueError('LDAP execution failed')

        def _new_uid():
            """Query the ldap directory for a new uidNumber."""
            # Get list of uid. Pick Max +1
            r = l.search_s(
                base=conf['ldap_base'],
                scope=ldap.SCOPE_SUBTREE,
                filterstr='(&(objectClass=posixAccount)(uidNumber=*))',
                attrlist=['uidNumber'])
            if len(r) > 0:
                return max(int(u[1]['uidNumber'][0]) for u in r) + 1        
            raise ValueError("fail to find new uidNumber")
        
        def _new_password():
            """Generate a new password."""
            table = string.ascii_letters + string.digits
            ''.join([table[ord(c) % len(table)] for c in os.urandom(12)])
            
            return base64.b64encode(os.urandom(8))[:-1].replace('==+/\\', '')
        
        def _ssha(password):
            """Convert the password a SSHA (base64 SHA hash + salt)"""
            salt = os.urandom(4)
            sha = hashlib.sha1(password)
            sha.update(salt)
            digest_salt_b64 = '{}{}'.format(sha.digest(), salt).encode('base64').strip()
            return '{{SSHA}}{}'.format(digest_salt_b64)
        
        try:
            # Build up expected user (should be bytes)
            ldap_membership_login_b = self.ldap_membership_login.encode('utf-8')
            name_b = self.name.encode('utf-8')
            attrs = {
                'cn': name_b,  # Common-name
                'givenName': name_b.partition(' ')[0],  # Firstname
                'sn': name_b.partition(' ')[2],  # Lastname
                'mail': self.email.encode('utf-8'),
            }
            
            # Search user in LDAP.
            search_filter = ldap.filter.filter_format(conf['ldap_filter'], (ldap_membership_login_b,))
            r = l.search_s(
                base=conf['ldap_base'],
                scope=ldap.SCOPE_SUBTREE,
                filterstr=search_filter,
                attrlist=attrs.keys())
            if len(r) == 0:
                # Generate a new password
                password = _new_password()
                # Define attributes that should never be changed.
                attrs['uid'] = ldap_membership_login_b
                attrs['uidNumber'] = str(_new_uid())
                attrs['gidNumber'] = str(10000)  # ldap-users
                attrs['loginShell'] = '/bin/bash'
                attrs['homeDirectory'] = '/home/%s' % (ldap_membership_login_b,)
                attrs['objectclass'] = ['inetOrgPerson', 'posixAccount', 'organizationalPerson', 'person', 'shadowAccount']
                attrs['userPassword'] = _ssha(password)
                
                # User doesn't exists. Add it
                dn = 'uid=%s,%s,%s' % (attrs['uid'], 'ou=People', conf['ldap_base'])
                ldif = modlist.addModlist(attrs)
                l.add_s(dn, ldif)
                
                # Send username and password by mail.
                ctx = dict(self._context, password=password)
                template_id = self.env['ir.model.data'].xmlid_to_object('pdsl_ldap_membership.new_password_email_template')
                template_id.with_context(ctx).send_mail(self.id)
                
                self.message_post(body=_("LDAP user %s / %s created") % (self.ldap_membership_login, password))
            else:
                # Generate a new password if required.
                if force_reset_password:
                    password = _new_password()
                    attrs['userPassword'] = _ssha(password)

                # Update the record.
                dn = r[0][0]
                old = r[0][1]
                ldif = modlist.modifyModlist(old, attrs)
                l.modify_s(dn, ldif)
                
                # Send username and password by mail.
                if force_reset_password:
                    ctx = dict(self._context, password=password)
                    template_id = self.env['ir.model.data'].xmlid_to_object('pdsl_ldap_membership.new_password_email_template')
                    template_id.with_context(ctx).send_mail(self.id)
                
                self.message_post(body=_("LDAP user %s updated") % self.ldap_membership_login)
                
        finally:
            # Close connection
            l.unbind_s()

    @api.multi
    def write(self, vals):
        """Override to create the group in LDAP."""
        res = super(ResPartner, self).write(vals)
        # Check if ldap mem
        if any(f in vals for f in ['ldap_membership_login', 'name', 'email']):
            self.pdsl_update_ldap_user()
        return res
