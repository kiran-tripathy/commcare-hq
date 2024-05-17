import json

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.test import Client, TestCase
from django.urls import reverse

from io import BytesIO
from openpyxl import Workbook
from unittest import mock

from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.locations.exceptions import LocationConsistencyError
from corehq.apps.locations.models import LocationType
from corehq.apps.locations.views import LocationTypesView, LocationImportView
from corehq.apps.users.models import WebUser, HQApiKey
from corehq.util.workbook_json.excel import WorkbookJSONError

OTHER_DETAILS = {
    'expand_from': None,
    'expand_to': None,
    'expand_from_root': False,
    'include_without_expanding': None,
    'include_only': [],
    'parent_type': '',
    'administrative': '',
    'shares_cases': False,
    'view_descendants': False,
}


class LocationTypesViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(LocationTypesViewTest, cls).setUpClass()
        cls.domain = "test-domain"
        cls.project = create_domain(cls.domain)
        cls.couch_user = WebUser.create(cls.domain, "test", "foobar", None, None)
        cls.couch_user.add_domain_membership(cls.domain, is_admin=True)
        cls.couch_user.set_role(cls.domain, "admin")
        cls.couch_user.save()
        cls.loc_type1 = LocationType(domain=cls.domain, name='type1', code='code1')
        cls.loc_type1.save()
        cls.loc_type2 = LocationType(domain=cls.domain, name='type2', code='code2')
        cls.loc_type2.save()

    def setUp(self):
        self.url = reverse(LocationTypesView.urlname, args=[self.domain])
        self.client = Client()
        self.client.login(username='test', password='foobar')

    @classmethod
    def tearDownClass(cls):
        cls.couch_user.delete(cls.domain, deleted_by=None)
        cls.project.delete()
        super(LocationTypesViewTest, cls).tearDownClass()

    @mock.patch('django_prbac.decorators.has_privilege', return_value=True)
    def send_request(self, data, _):
        return self.client.post(self.url, {'json': json.dumps(data)})

    def test_missing_property(self):
        with self.assertRaises(LocationConsistencyError):
            self.send_request({'loc_types': [{}]})

    def test_swap_name(self):
        loc_type1 = OTHER_DETAILS.copy()
        loc_type2 = OTHER_DETAILS.copy()
        loc_type1.update({'name': self.loc_type2.name, 'pk': self.loc_type1.pk})
        loc_type2.update({'name': self.loc_type1.name, 'pk': self.loc_type2.pk})
        data = {'loc_types': [loc_type1, loc_type2]}
        response = self.send_request(data)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(
            str(messages[0].message),
            'Looks like you are assigning a location name/code to a different location in the same request. '
            'Please do this in two separate updates by using a temporary name to free up the name/code to be '
            're-assigned.'
        )

    def test_swap_code(self):
        loc_type1 = OTHER_DETAILS.copy()
        loc_type2 = OTHER_DETAILS.copy()
        loc_type1.update({'name': self.loc_type1.name, 'pk': self.loc_type1.pk, 'code': self.loc_type2.code})
        loc_type2.update({'name': self.loc_type2.name, 'pk': self.loc_type2.pk, 'code': self.loc_type1.code})
        data = {'loc_types': [loc_type1, loc_type2]}
        response = self.send_request(data)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(
            str(messages[0].message),
            'Looks like you are assigning a location name/code to a different location in the same request. '
            'Please do this in two separate updates by using a temporary name to free up the name/code to be '
            're-assigned.'
        )

    def test_valid_update(self):
        loc_type1 = OTHER_DETAILS.copy()
        loc_type2 = OTHER_DETAILS.copy()
        loc_type1.update({'name': "new name", 'pk': self.loc_type1.pk, 'code': self.loc_type1.code})
        loc_type2.update({'name': "new name 2", 'pk': self.loc_type2.pk, 'code': self.loc_type2.code})
        data = {'loc_types': [loc_type1, loc_type2]}
        response = self.send_request(data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)


class BulkLocationUploadAPITest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(BulkLocationUploadAPITest, cls).setUpClass()
        cls.domain_name = 'bulk-upload-domain'
        cls.domain = create_domain(cls.domain_name)
        cls.domain.save()
        cls.addClassCleanup(cls.domain.delete)
        cls.user = WebUser.create(cls.domain_name, 'test@test.com', 'password', created_by=None, created_via=None)
        cls.addClassCleanup(cls.user.delete, cls.domain_name, deleted_by=None)
        cls.api_key = HQApiKey.objects.create(user=cls.user.get_django_user(), domain=cls.domain_name)

    def setUp(self):
        self.client = Client()
        self.url = reverse('bulk_location_upload_api', args=[self.domain_name])

    @mock.patch('corehq.apps.locations.views.import_locations_async')
    @mock.patch('corehq.apps.locations.views.LocationImportView.cache_file')
    def test_success(self, mock_cache_file, mock_import_locations_async):
        mock_file_ref = mock.MagicMock()
        mock_file_ref.download_id = 'mock_download_id'
        mock_file_ref.set_task = mock.MagicMock()
        mock_cache_file.return_value = LocationImportView.Ref(mock_file_ref)
        mock_import_locations_async.delay.return_value = None

        workbook = Workbook()
        file = BytesIO()
        workbook.save(file)
        file.seek(0)
        file.name = 'mock_file.xlsx'

        response = self.client.post(
            self.url,
            {'bulk_upload_file': file},
            HTTP_AUTHORIZATION=f'ApiKey {self.user.username}:{self.api_key.key}',
            format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True})

        mock_cache_file.assert_called_once()
        _, call_args, call_kwargs = mock_cache_file.mock_calls[0]
        self.assertIsInstance(call_args[0], WSGIRequest)
        self.assertEqual(call_args[1], self.domain_name)
        self.assertIsInstance(call_args[2], InMemoryUploadedFile)
        self.assertEqual(call_args[2].name, 'mock_file.xlsx')

        mock_import_locations_async.delay.assert_called_once_with(
            self.domain_name, 'mock_download_id', self.user.user_id
        )
        mock_file_ref.set_task.assert_called_once()

    def test_api_no_authentication(self):
        response = self.client.post(self.url, {'bulk_upload_file': 'mock_file'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content.decode(), 'Authorization Required')

    def test_api_invalid_authentication(self):
        response = self.client.post(
            self.url,
            {'bulk_upload_file': 'mock_file'},
            HTTP_AUTHORIZATION=f'ApiKey {self.user.username}:invalid_key'
        )
        self.assertEqual(response.status_code, 401)

    def test_no_file_uploaded(self):
        response = self.client.post(
            self.url,
            HTTP_AUTHORIZATION=f'ApiKey {self.user.username}:{self.api_key.key}',
            format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'success': False, 'message': 'no file uploaded'})

    @mock.patch('corehq.apps.locations.views.get_workbook')
    def test_invalid_file_format(self, mock_get_workbook):
        mock_get_workbook.side_effect = WorkbookJSONError('Invalid file format')
        file = BytesIO(b'invalid file content')
        file.name = 'invalid_file.txt'
        response = self.client.post(
            self.url,
            {'bulk_upload_file': file},
            HTTP_AUTHORIZATION=f'ApiKey {self.user.username}:{self.api_key.key}',
            format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'success': False, 'message': 'Invalid file format'})

    @mock.patch('corehq.apps.locations.views.get_redis_lock')
    def test_concurrent_update_in_progress(self, mock_get_redis_lock):
        mock_lock = mock.MagicMock()
        mock_lock.acquire.return_value = False
        mock_get_redis_lock.return_value = mock_lock

        workbook = Workbook()
        file = BytesIO()
        workbook.save(file)
        file.seek(0)
        file.name = 'file.xlsx'

        response = self.client.post(
            self.url,
            {'bulk_upload_file': file},
            HTTP_AUTHORIZATION=f'ApiKey {self.user.username}:{self.api_key.key}',
            format='multipart'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'success': False,
            'message': 'Some of the location edits are still in progress, '
                       'please wait until they finish and then try again'
        })
