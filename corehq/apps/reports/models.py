from corehq.apps.reports.exceptions import TableauAPIError
import jwt
import json
import logging
import requests
import sys
import uuid

from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, gettext_noop


from dimagi.ext.couchdbkit import IntegerProperty

from corehq.apps.reports.const import TABLEAU_ROLES
from corehq.apps.users.models import CommCareUser
from corehq.motech.utils import b64_aes_decrypt, b64_aes_encrypt


class HQUserType(object):
    ACTIVE = 0
    DEMO_USER = 1
    ADMIN = 2
    UNKNOWN = 3
    COMMTRACK = 4
    DEACTIVATED = 5
    WEB = 6
    human_readable = [settings.COMMCARE_USER_TERM,
                      gettext_noop("demo_user"),
                      gettext_noop("admin"),
                      gettext_noop("Unknown Users"),
                      gettext_noop("CommCare Supply"),
                      gettext_noop("Deactivated Mobile Workers"),
                      gettext_noop("Web Users"), ]
    toggle_defaults = (True, False, False, False, False, True, True)
    count = len(human_readable)
    included_defaults = (True, True, True, True, False, True, True)

    @classmethod
    def use_defaults(cls):
        return cls._get_manual_filterset(cls.included_defaults, cls.toggle_defaults)

    @classmethod
    def all_but_users(cls):
        no_users = [True] * cls.count
        no_users[cls.ACTIVE] = False
        return cls._get_manual_filterset(cls.included_defaults, no_users)

    @classmethod
    def commtrack_defaults(cls):
        # this is just a convenience method for clarity on commtrack projects
        return cls.all()

    @classmethod
    def all(cls):
        defaults = (True,) * cls.count
        return cls._get_manual_filterset(defaults, cls.toggle_defaults)

    @classmethod
    def _get_manual_filterset(cls, included, defaults):
        """
        manually construct a filter set. included and defaults should both be
        arrays of booleans mapping to values in human_readable and whether they should be
        included and defaulted, respectively.
        """
        return [HQUserToggle(i, defaults[i]) for i in range(cls.count) if included[i]]

    @classmethod
    def use_filter(cls, ufilter):
        return [HQUserToggle(i, str(i) in ufilter) for i in range(cls.count)]


class HQToggle(object):
    type = None
    show = False
    name = None

    def __init__(self, type, show, name):
        self.type = type
        self.name = name
        self.show = show

    def __repr__(self):
        return "%(klass)s[%(type)s:%(show)s:%(name)s]" % dict(
            klass=self.__class__.__name__,
            type=self.type,
            name=self.name,
            show=self.show
        )


class HQUserToggle(HQToggle):

    def __init__(self, type, show):
        name = _(HQUserType.human_readable[type])
        super(HQUserToggle, self).__init__(type, show, name)


class TempCommCareUser(CommCareUser):
    filter_flag = IntegerProperty()

    def __init__(self, domain, username, uuid):
        if username == HQUserType.human_readable[HQUserType.DEMO_USER]:
            filter_flag = HQUserType.DEMO_USER
        elif username == HQUserType.human_readable[HQUserType.ADMIN]:
            filter_flag = HQUserType.ADMIN
        else:
            filter_flag = HQUserType.UNKNOWN
        super(TempCommCareUser, self).__init__(
            domain=domain,
            username=username,
            _id=uuid,
            date_joined=datetime.utcnow(),
            is_active=False,
            first_name='',
            last_name='',
            filter_flag=filter_flag
        )

    def save(self, **params):
        raise NotImplementedError

    @property
    def userID(self):
        return self._id

    @property
    def username_in_report(self):
        if self.filter_flag == HQUserType.UNKNOWN:
            final = format_html('{} <strong>[unregistered]</strong>', self.username)
        elif self.filter_flag == HQUserType.DEMO_USER:
            final = format_html('<strong>{}</strong>', self.username)
        else:
            final = format_html('<strong>{}</strong> ({})', self.username, self.user_id)
        return final

    @property
    def raw_username(self):
        return self.username

    class Meta(object):
        app_label = 'reports'


class AppNotFound(Exception):
    pass


class TableauServer(models.Model):
    SERVER_TYPES = (
        ('server', gettext_lazy('Tableau Server')),
        ('online', gettext_lazy('Tableau Online')),
    )
    domain = models.CharField(max_length=64, default='')
    server_type = models.CharField(max_length=6, choices=SERVER_TYPES, default='server')
    server_name = models.CharField(max_length=128)
    validate_hostname = models.CharField(max_length=128, default='', blank=True)
    target_site = models.CharField(max_length=64, default='Default')

    def __str__(self):
        return '{server} {server_type} {site}'.format(server=self.server_name,
                                                      server_type=self.server_type,
                                                      site=self.target_site)


class TableauVisualization(models.Model):
    title = models.CharField(max_length=32, null=True)
    domain = models.CharField(max_length=64)
    server = models.ForeignKey(TableauServer, on_delete=models.CASCADE)
    view_url = models.CharField(max_length=256)
    upstream_id = models.CharField(max_length=32, null=True)

    @property
    def name(self):
        return '/'.join(self.view_url.split('?')[0].split('/')[-2:])

    def __str__(self):
        return '{domain} {server} {view}'.format(domain=self.domain,
                                                 server=self.server,
                                                 view=self.view_url[0:64])

    @classmethod
    def for_user(cls, domain, couch_user):
        items = [
            viz
            for viz in TableauVisualization.objects.filter(domain=domain)
            if couch_user.can_view_tableau_viz(domain, f"{viz.id}")
        ]
        return sorted(items, key=lambda v: v.name.lower())


class TableauConnectedApp(models.Model):
    app_client_id = models.CharField(max_length=32)
    secret_id = models.CharField(max_length=64)
    encrypted_secret_value = models.CharField(max_length=64)
    server = models.OneToOneField(TableauServer, on_delete=models.CASCADE)

    def __str__(self):
        return 'App client ID: {app_client_id},  Server: {server}'.format(app_client_id=self.app_client_id,
                                                                          server=self.server)

    @property
    def plaintext_secret_value(self):
        return b64_aes_decrypt(self.encrypted_secret_value)

    @plaintext_secret_value.setter
    def plaintext_secret_value(self, plaintext):
        self.encrypted_secret_value = b64_aes_encrypt(plaintext)

    def create_jwt(self):
        connected_app_permissions = ["tableau:users:read", "tableau:users:create", "tableau:users:update",
                                     "tableau:users:delete", "tableau:groups:read", "tableau:groups:create",
                                     "tableau:groups:update", "tableau:groups:delete"]
        token = jwt.encode(
            {
                "iss": self.app_client_id,
                "exp": datetime.utcnow() + timedelta(minutes=5),
                "jti": str(uuid.uuid4()),
                "aud": "tableau",
                "sub": "HQ_integration_admin",
                "scp": connected_app_permissions
            },
            self.plaintext_secret_value,
            algorithm="HS256",
            headers={
                'kid': self.secret_id,
                'iss': self.app_client_id
            }
        )
        return token


class TableauGroup(models.Model):
    server = models.ForeignKey(TableauServer, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    group_id = models.CharField(max_length=32)


class TableauUser(models.Model):
    server = models.ForeignKey(TableauServer, on_delete=models.CASCADE)
    username = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=TABLEAU_ROLES)
    groups = models.ManyToManyField(TableauGroup)
    tableau_user_id = models.CharField(max_length=64)
    last_synced = models.DateTimeField(auto_now=True)


logger = logging.getLogger('tableau_api')


class TableauAPISession(object):

    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'

    def __init__(self, connected_app):
        self.tableau_connected_app = connected_app
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        api_version = self._get_api_version(self.tableau_connected_app)
        self.base_url = f'https://{connected_app.server.server_name}/api/{api_version}'
        self.signed_in = False
        self.site_id = None

    def _get_api_version(self, connected_app):
        response_body = self._make_request(
            self.GET,
            'Get API version',
            f'https://{connected_app.server.server_name}/api/2.4/serverinfo',
            {},
            requires_sign_in=False
        )
        return response_body['serverInfo']['restApiVersion']

    def _make_request(self, method, request_name, url, data, requires_sign_in=True):
        if requires_sign_in:
            self._verify_signed_in()
        logger.info(f"Making Tableau API request '{request_name}'.")
        response = requests.request(method, url, data=json.dumps(data), headers=self.headers)
        if response.ok:
            logger.info(f"Tableau API request '{request_name}' was succussful.")
            if response.text:
                body = json.loads(response.text)
                return body
        else:
            raise TableauAPIError(f"Tableau API request '{request_name}' failed. Response body: {response.text}")

    def sign_in(self):
        response_body = self._make_request(
            self.POST,
            'Sign In',
            self.base_url + '/auth/signin',
            {
                "credentials": {
                    "jwt": self.tableau_connected_app.create_jwt(),
                    "site": {
                        "contentUrl": self.tableau_connected_app.server.target_site
                    }
                }
            },
            requires_sign_in=False
        )
        auth_token = response_body['credentials']['token']
        self.headers.update({'X-Tableau-Auth': auth_token})
        self.site_id = response_body['credentials']['site']['id']
        self.signed_in = True

    def _verify_signed_in(self):
        if not self.signed_in:
            raise TableauAPIError("You must be signed in to the API to call that method.")

    def sign_out(self):
        self._make_request(
            self.POST,
            'Sign Out',
            self.base_url + '/auth/signout',
            {}
        )
        self.signed_in = False
        del self.headers['X-Tableau-Auth']
        self.site_id = None

    def query_groups(self, name=None):
        '''
        Include `name` arg to get information for a specific group (like the group ID). Case sensitive.
        Exclude the `name` arg to get a list of all groups on the site.

        Each group dict returned has this format, at a minumum:
        {
            "domain": {
                "name": ...
            },
            "id": ...,
            "name": ...
        }
        '''
        url = self.base_url + f'/sites/{self.site_id}/groups?pageSize=1000'
        if name:
            url += f'&filter=name:eq:{name}'
        response_body = self._make_request(
            self.GET,
            'Query Groups',
            url,
            {}
        )
        if name:
            return response_body['groups']['group'][0]
        else:
            if 1000 < int(response_body['pagination']['totalAvailable']):
                raise TableauAPIError("Error: API does not work with more than 1000 groups on a single site.")
            return response_body['groups']['group']

    def get_users_in_group(self, group_id):
        '''
        Returns a list of users in the group with the given ID. Return value format:
        [
            {
                "externalAuthUserId': "",
                "id": ...,
                "name": ...,
                "siteRole": ...,
                "locale": ...,
                "language": ...},
            },
            ...
        ]
        '''
        page_size = 100
        page_number = 1
        total_users = sys.maxsize
        tableau_users = []
        while (page_size * (page_number - 1) < total_users):
            response_body = self._make_request(
                self.GET,
                'Get Users in Group',
                (self.base_url
                + f'/sites/{self.site_id}/groups/{group_id}/users?pageSize={page_size}&pageNumber={page_number}'),
                {}
            )
            tableau_users += response_body['users']['user']
            if page_number == 1:
                total_users = int(response_body['pagination']['totalAvailable'])
            page_number += 1
        return tableau_users

    def create_group(self, group_name, min_site_role):
        '''
        Creates a Tableau group with the given name, and assigns the given role to the group.
        Returns the group ID.
        '''
        response_body = self._make_request(
            self.POST,
            'Create Group',
            self.base_url + f'/sites/{self.site_id}/groups',
            {
                "group": {
                    "name": f"{group_name}",
                    "minimumSiteRole": f"{min_site_role}"
                }
            }
        )
        return response_body['group']['id']

    def add_user_to_group(self, user_id, group_id):
        '''
        Adds the Tableau user with the given ID to the group with the given ID.
        '''
        self._make_request(
            self.POST,
            'Add User to Group',
            self.base_url + f'/sites/{self.site_id}/groups/{group_id}/users',
            {
                "user": {
                    "id": f"{user_id}"
                }
            }
        )
        return True

    def get_groups_for_user_id(self, id):
        '''
        Returns the list of groups that the user with the given ID belongs to. Return value format:
        [
            {
                "domain": {
                    "name": ... # The group's domain's name
                },
                "id": ...,
                "name": ... # The group's actual name
            },
            ...
        ]
        '''
        page_size = 1000
        page_number = 1
        response_body = self._make_request(
            self.GET,
            'Get Groups for User',
            (self.base_url
            + f'/sites/{self.site_id}/users/{id}/groups?pageSize={page_size}&pageNumber={page_number}'),
            {}
        )
        if 1000 < int(response_body['pagination']['totalAvailable']):
            raise TableauAPIError("Error: API does not work where a user belongs to more than 1000 groups.")
        return response_body['groups']['group']

    def create_user(self, username, role):
        '''
        Adds a user to Tableau with the given username and role. Returns the ID of the created user.
        '''
        response_body = self._make_request(
            self.POST,
            'Create User',
            self.base_url + f'/sites/{self.site_id}/users',
            {
                "user": {
                    "name": f"{username}",
                    "siteRole": f"{role}"
                }
            }
        )
        return response_body['user']['id']

    def update_user(self, id, role):
        '''
        Updates the user with the given ID to have the given role.
        '''
        self._make_request(
            self.PUT,
            'Update User',
            self.base_url + f'/sites/{self.site_id}/users/{id}',
            {
                "user": {
                    "siteRole": f"{role}"
                }
            }
        )
        return True

    def delete_user(self, id):
        '''
        Deletes the user with the given ID.
        '''
        self._make_request(
            self.DELETE,
            'Delete User',
            self.base_url + f'/sites/{self.site_id}/users/{id}',
            {}
        )
        return True
