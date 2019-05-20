from __future__ import absolute_import
from __future__ import unicode_literals

import mock
from django.test import SimpleTestCase

from custom.icds.tasks import setup_ccz_file_for_hosting
from custom.icds.models import (
    HostedCCZ,
    CCZHostingLink,
)


@mock.patch('custom.icds.tasks.ccz_hosting.open')
@mock.patch('custom.icds.tasks.ccz_hosting.wrap_app')
@mock.patch('custom.icds.tasks.ccz_hosting.get_build_doc_by_version')
@mock.patch('custom.icds.tasks.ccz_hosting.create_files_for_ccz')
@mock.patch('custom.icds.tasks.ccz_hosting.HostedCCZ.objects.get')
@mock.patch('custom.icds.models.CCZHostingUtility')
class TestSetUpCCZFileForHosting(SimpleTestCase):
    def setUp(self):
        super(TestSetUpCCZFileForHosting, self).setUp()
        self.link = CCZHostingLink(username="username", password="password", identifier="link1234", domain="test")
        self.ccz_hosting = HostedCCZ(link=self.link, app_id="dummy", version=12, profile_id="123456")

    def test_hosting_not_present(self, mock_ccz_utility, mock_get, *_):
        mock_result = mock.MagicMock()
        mock_result.return_value = True
        mock_ccz_utility.return_value.file_exists = mock_result
        mock_get.side_effect = HostedCCZ.DoesNotExist
        setup_ccz_file_for_hosting(3)
        self.assertFalse(mock_result.called)

    def test_ccz_already_present(self, mock_ccz_utility, mock_get, mock_create_ccz, *_):
        mock_result = mock.MagicMock()
        mock_result.return_value = True
        mock_ccz_utility.return_value.file_exists = mock_result
        mock_get.return_value = self.ccz_hosting
        mock_result.return_value = True
        setup_ccz_file_for_hosting(3)
        self.assertTrue(mock_result.called)
        self.assertFalse(mock_create_ccz.called)

    def test_ccz_not_already_present(self, mock_ccz_utility, mock_get, mock_create_ccz, mock_get_build, *_):
        mock_get.return_value = self.ccz_hosting

        mock_result = mock.MagicMock()
        mock_result.return_value = False
        mock_ccz_utility.return_value.file_exists = mock_result

        setup_ccz_file_for_hosting(3)

        self.assertTrue(mock_result.called)
        mock_get_build.assert_called_with(self.ccz_hosting.domain, self.ccz_hosting.app_id,
                                          self.ccz_hosting.version)
        self.assertTrue(mock_create_ccz.called)
        self.assertTrue(mock_ccz_utility.return_value.store_file_in_blobdb.called)

    def test_ccz_creation_fails(self, mock_ccz_utility, mock_get, mock_create_ccz, mock_get_build, *_):
        mock_get.return_value = self.ccz_hosting

        mock_result = mock.MagicMock()
        mock_result.return_value = False
        mock_ccz_utility.return_value.file_exists = mock_result

        mock_delete_ccz = mock.MagicMock()
        self.ccz_hosting.delete_ccz = mock_delete_ccz
        mock_delete_ccz.return_value = True

        mock_store = mock.MagicMock()
        mock_ccz_utility.return_value.store_file_in_blobdb = mock_store
        mock_store.side_effect = Exception("Fail hard!")
        with self.assertRaisesMessage(Exception, "Fail hard!"):
            setup_ccz_file_for_hosting(3)

        mock_get_build.assert_called_with(self.ccz_hosting.domain, self.ccz_hosting.app_id,
                                          self.ccz_hosting.version)
        self.assertTrue(mock_create_ccz.called)
        self.assertTrue(mock_ccz_utility.return_value.store_file_in_blobdb.called)
        self.assertTrue(mock_delete_ccz.called)
