
"""
couch models go here
"""
from __future__ import absolute_import

from datetime import datetime
from django.contrib.auth.models import User
from django.db import models
from django.http import Http404
from corehq.apps.domain.decorators import login_and_domain_required
from dimagi.utils.couch.database import get_db
from djangocouchuser.models import CouchUserProfile
from couchdbkit.ext.django.schema import *
from couchdbkit.schema.properties_proxy import SchemaListProperty
from djangocouch.utils import model_to_doc
from corehq.apps.domain.models import Domain
from corehq.apps.domain.shortcuts import create_user
from corehq.apps.users.util import django_user_from_couch_id, \
    couch_user_from_django_user
from dimagi.utils.mixins import UnicodeMixIn
import logging
from corehq.apps.reports.models import ReportNotification
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from dimagi.utils.django.email import send_HTML_email

COUCH_USER_AUTOCREATED_STATUS = 'autocreated'

def _add_to_list(list, obj, default):
    if obj in list:
        list.remove(obj)
    if default:
        ret = [obj]
        ret.extend(list)
        return ret
    else:
        list.append(obj)
    return list
    
    
def _get_default(list):
    return list[0] if list else None

class Permissions(object):
    EDIT_USERS = 'edit-users'
    EDIT_DATA = 'edit-data'
    EDIT_APPS = 'edit-apps'
    AVAILABLE_PERMISSIONS = [EDIT_DATA, EDIT_USERS, EDIT_APPS]
    
class DomainMembership(Document):
    """
    Each user can have multiple accounts on the 
    web domain. This is primarily for Dimagi staff.
    """

    domain = StringProperty()
    is_admin = BooleanProperty(default=False)
    permissions = StringListProperty()
    last_login = DateTimeProperty()
    date_joined = DateTimeProperty()
    
    class Meta:
        app_label = 'users'

class Login(DocumentSchema):
    username = StringProperty()
    password = StringProperty()

class Account(Document):
    # the UUID which is also the login doc's _id
    login_id = StringProperty()

    @property
    def login(self):
        try:
            return Login.wrap(get_db().get(self.login_id)['django_user'])
        except:
            return None


    def username_html(self):
        username = self.login['username']
        html = "<span class='user_username'>%s</span>" % username
        return html

    class Meta:
        app_label = 'users'
        
class CommCareAccount(Account):
    """
    This is the information associated with a 
    particular commcare user. Right now, we 
    associate one commcare user to one web user
    (with multiple domain logins, phones, SIMS)
    but we could always extend to multiple commcare
    users if desired later.
    """

    registering_device_id = StringProperty()
    user_data = DictProperty()
    domain = StringProperty()

    def username_html(self):
        username = self.login['username']
        if '@' in username:
            html = "<span class='user_username'>%s</span><span class='user_domainname'>@%s</span>" % \
                   tuple(username.split('@'))
        else:
            html = "<span class='user_username'>%s</span>" % username
        return html
    
    class Meta:
        app_label = 'users'

    @classmethod
    def get_by_userID(cls, userID):
        return cls.view('users/commcare_users_by_login_id', key=userID).one()
    
class WebAccount(Account):
    domain_memberships = SchemaListProperty(DomainMembership)

    class Meta:
        app_label = 'users'

class CouchUser(Document, UnicodeMixIn):

    """
    a user (for web+commcare+sms)
    can be associated with multiple username/password/login tuples
    can be associated with multiple phone numbers/SIM cards
    can be associated with multiple phones/device IDs
    """
    # not used e.g. when user is only a commcare user

    first_name = StringProperty()
    last_name = StringProperty()
    email = StringProperty()

    # the various commcare accounts associated with this user
    web_account = SchemaProperty(WebAccount)
    commcare_accounts = SchemaListProperty(CommCareAccount)
    
    device_ids = ListProperty()
    phone_numbers = ListProperty()

    created_on = DateTimeProperty()
    
    """
    For now, 'status' is things like:
        ('auto_created',     'Automatically created from form submission.'),   
        ('phone_registered', 'Registered from phone'),    
        ('site_edited',     'Manually added or edited from the HQ website.'),        
    """
    status = StringProperty()

    _user = None
    _user_checked = False

    class Meta:
        app_label = 'users'
    
    def __unicode__(self):
        return "couch user %s" % self.get_id
    
    @property
    def default_django_user(self):
        login_id = ""
        # first choice: web user login
        if self.web_account.login_id:
            login_id = self.web_account.login_id
        # second choice: latest registered commcare account
        elif self.commcare_accounts:
            login_id = _get_default(self.commcare_accounts).login_id
        else:
            raise User.DoesNotExist("This couch user doesn't have a linked django login!")
        return django_user_from_couch_id(login_id)


    def get_email(self):
        return self.email or self.default_django_user.email
    @property
    def formatted_name(self):
        return "%s %s" % (self.first_name, self.last_name)
    
    @property
    def default_account(self):
        if self.web_account.login_id:
            return self.web_account
        else:
            return self.default_commcare_account

    @property
    def account_type(self):
        if self.web_account.login_id:
            return "WebAccount"
        else:
            return "CommCareAccount"
        
    @property
    def username(self):
        return self.default_account.login.username
    @property
    def raw_username(self):
        if self.account_type == "CommCareAccount":
            return self.username.split("@")[0]
        else:
            return self.username
    @property
    def userID(self):
        return self.default_account.login_id
        
    def get_scheduled_reports(self):
        return ReportNotification.view("reports/user_notifications", key=self.get_id, include_docs=True).all()
    
    def save(self, *args, **kwargs):
        # Call the "real" save() method.
        super(CouchUser, self).save(*args, **kwargs) 
    
    def delete(self, *args, **kwargs):
        try:
            user = self.get_django_user()
            user.delete()
        except User.DoesNotExist:
            pass
        super(CouchUser, self).delete(*args, **kwargs) # Call the "real" delete() method.
    
    def add_django_user(self, username, password, **kwargs):
        # DO NOT implement this. It will create an endless loop.
        raise NotImplementedError

    def get_django_user(self):
        return User.objects.get(username=self.web_account.login_id)

    def get_domain_membership(self, domain):
        for d in self.web_account.domain_memberships:
            if d.domain == domain:
                return d
    
    def add_domain_membership(self, domain, **kwargs):
        for d in self.web_account.domain_memberships:
            if d.domain == domain:
                # membership already exists
                return
        self.web_account.domain_memberships.append(DomainMembership(domain=domain,
                                                        **kwargs))

    def is_domain_admin(self, domain=None):
        if not domain:
            # hack for template
            if hasattr(self, 'current_domain'):
                # this is a hack needed because we can't pass parameters from views
                domain = self.current_domain
            else:
                return False # no domain, no admin
        if self.web_account.login.is_superuser:
            return True
        dm = self.get_domain_membership(domain)
        if dm:
            return dm.is_admin
        else:
            return False

    @property
    def domain_names(self):
        return [dm.domain for dm in self.web_account.domain_memberships]

    def get_active_domains(self):
        domain_names = self.domain_names
        return Domain.objects.filter(name__in=domain_names)

    def is_member_of(self, domain_qs):
        membership_count = domain_qs.filter(name__in=self.domain_names).count()
        if membership_count > 0:
            return True
        return False
    
    def add_commcare_account(self, django_user, domain, device_id, user_data={}, **kwargs):
        """
        Adds a commcare account to this. 
        """
        commcare_account = CommCareAccount(login_id=django_user.get_profile()._id,
                                           domain=domain,
                                           registering_device_id=device_id,
                                           user_data=user_data,
                                           **kwargs)
        
        self.commcare_accounts = _add_to_list(self.commcare_accounts, commcare_account, default=True)
        
    @property
    def default_commcare_account(self, domain=None):
        if hasattr(self, 'current_domain'):
            # this is a hack needed because we can't pass parameters from views
            domain = self.current_domain
        if domain:
            for account in self.commcare_accounts:
                if account.domain == domain:
                    return account
        else:
            return _get_default(self.commcare_accounts)
    
    def link_commcare_account(self, domain, from_couch_user_id, commcare_login_id, **kwargs):
        from_couch_user = CouchUser.get(from_couch_user_id)
        for i in range(0, len(from_couch_user.commcare_accounts)):
            if from_couch_user.commcare_accounts[i].login_id == commcare_login_id:
                # this generates a 'document update conflict'. why?
                self.commcare_accounts.append(from_couch_user.commcare_accounts[i])
                self.save()
                del from_couch_user.commcare_accounts[i]
                from_couch_user.save()
                return
    
    def unlink_commcare_account(self, domain, commcare_user_index, **kwargs):
        commcare_user_index = int(commcare_user_index)
        c = CouchUser()
        c.created_on = datetime.now()
        original = self.commcare_accounts[commcare_user_index]
        c.commcare_accounts.append(original)
        c.status = 'unlinked from %s' % self._id
        c.save()
        # is there a more atomic way to do this?
        del self.commcare_accounts[commcare_user_index]
        self.save()
        
    def add_device_id(self, device_id, default=False, **kwargs):
        """ Don't add phone devices if they already exist """
        self.device_ids = _add_to_list(self.device_ids, device_id, default)
    
    def add_phone_number(self, phone_number, default=False, **kwargs):
        """ Don't add phone numbers if they already exist """
        if not isinstance(phone_number, basestring):
            phone_number = str(phone_number)
        self.phone_numbers = _add_to_list(self.phone_numbers, phone_number, default)
    @property
    def default_phone_number(self):
        return _get_default(self.phone_numbers)
    
    @property
    def couch_id(self):
        return self._id
    
    @classmethod
    def from_web_user(cls, user):
        login_id = user.get_profile()._id
        assert(len(cls.view("users/couch_users_by_django_profile_id", include_docs=True, key=login_id)) == 0)
        couch_user = cls()
        couch_user.web_account.login_id = login_id
        couch_user.first_name = user.first_name
        couch_user.last_name = user.last_name
        couch_user.email = user.email
        return couch_user

    # Couch view wrappers
    @classmethod
    def phone_users_by_domain(cls, domain):
        return CouchUser.view("users/phone_users_by_domain",
            startkey=[domain],
            endkey=[domain, {}],
            include_docs=True,
        )
    @classmethod
    def commcare_users_by_domain(cls, domain):
        return CouchUser.view("users/commcare_users_by_domain",
            reduce=False,
            key=domain,
            include_docs=True,
        )

    def set_permission(self, domain, permission, value, save=True):
        assert(permission in Permissions.AVAILABLE_PERMISSIONS)
        if self.has_permission(domain, permission) == value:
            return
        dm = self.get_domain_membership(domain)
        if value:
            dm.permissions.append(permission)
        else:
            dm.permissions = [p for p in dm.permissions if p != permission]
        if save:
            self.save()
    def reset_permissions(self, domain, permissions, save=True):
        dm = self.get_domain_membership(domain)
        dm.permissions = permissions
        if save:
            self.save()

    def has_permission(self, domain, permission):
        # is_admin is the same as having all the permissions set
        dm = self.get_domain_membership(domain)
        if self.is_domain_admin(domain):
            return True
        else:
            return permission in dm.permissions

    # these functions help in templates
    def can_edit_apps(self, domain):
        return self.has_permission(domain, Permissions.EDIT_APPS)
    def can_edit_users(self, domain):
        return self.has_permission(domain, Permissions.EDIT_USERS)


def require_permission(permission):
    def decorator(view_func):
        def _inner(request, domain, *args, **kwargs):
            if hasattr(request, "couch_user") and (request.user.is_superuser or request.couch_user.has_permission(domain, permission)):
                return login_and_domain_required(view_func)(request, domain, *args, **kwargs)
            else:
                raise Http404()
        return _inner
    return decorator



"""
Django  models go here
"""
class Invitation(Document):
    """
    When we invite someone to a domain it gets stored here.
    """
    domain = StringProperty()
    email = StringProperty()
    is_domain_admin = BooleanProperty()
    invited_by = StringProperty()
    invited_on = DateTimeProperty()
    is_accepted = BooleanProperty(default=False)
    
    _inviter = None
    def get_inviter(self):
        if self._inviter == None:
            self._inviter = CouchUser.get(self.invited_by)
        return self._inviter
    
    def send_activation_email(self):

        url = "http://%s%s" % (Site.objects.get_current().domain, 
                               reverse("accept_invitation", args=[self.domain, self.get_id]))
        params = {"domain": self.domain, "url": url, "inviter": self.get_inviter().formatted_name}
        text_content = render_to_string("domain/email/domain_invite.txt", params)
        html_content = render_to_string("domain/email/domain_invite.html", params)
        subject = 'Invitation from %s to join CommCareHQ' % self.get_inviter().formatted_name        
        send_HTML_email(subject, self.email, text_content, html_content)

    
    
class HqUserProfile(CouchUserProfile):
    """
    The CoreHq Profile object, which saves the user data in couch along
    with annotating whatever additional fields we need for Hq
    (Right now, none additional are required)
    """
    
    class Meta:
        app_label = 'users'
    
    def __unicode__(self):
        return "%s" % (self.user)

    def get_couch_user(self):
        return couch_user_from_django_user(self.user)
        
def create_hq_user_from_commcare_registration_info(domain, username, password,
                                                   uuid='', device_id='',
                                                   date='', user_data={},
                                                   **kwargs):
    """ na 'commcare user' is a couch user which:
    * does not have a web user
    * does have an associated commcare account,
        * has a django account linked to the commcare account for httpdigest auth
    """
    
    # create django user for the commcare account
    login = create_user(username, password, uuid=uuid)
    
    # create new couch user
    couch_user = CouchUser()
    
    # populate the couch user
    if not date:
        date = datetime.now()
    couch_user.add_commcare_account(login, domain, device_id, user_data)
    couch_user.add_device_id(device_id=device_id)
    couch_user.save()
    return couch_user
    

    
# make sure our signals are loaded
import corehq.apps.users.signals
