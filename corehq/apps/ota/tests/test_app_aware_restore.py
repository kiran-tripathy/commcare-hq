from django.test import TestCase
from mock import patch

from casexml.apps.phone.tests.utils import create_restore_user
from corehq import toggles
from corehq.apps.app_manager.fixtures.mobile_ucr import report_fixture_generator
from corehq.apps.app_manager.models import Application, ReportModule, ReportAppConfig
from corehq.apps.users.dbaccessors.all_commcare_users import delete_all_users
from corehq.apps.domain.models import Domain
from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.userreports.tests.utils import get_sample_report_config


class AppAwareSyncTests(TestCase):
    domain = 'test_domain'
    rows = [{
        'owner': 'bob',
        'count': 3,
        'is_starred': True
    }]

    @classmethod
    def setUpClass(cls):
        delete_all_users()
        create_domain(cls.domain)
        toggles.MOBILE_UCR.set(cls.domain, True, toggles.NAMESPACE_DOMAIN)
        cls.user = create_restore_user(cls.domain)

        cls.app1 = Application.new_app(cls.domain, 'Test App 1')
        cls.report_config1 = get_sample_report_config()
        cls.report_config1.domain = cls.domain
        cls.report_config1.save()
        report_app_config = {
            'report_id': cls.report_config1.get_id,
            'uuid': '123456'
        }
        module = cls.app1.add_module(ReportModule.new_module('Reports', None))
        module.report_configs = [ReportAppConfig.wrap(report_app_config)]
        cls.app1.save()

        cls.app2 = Application.new_app(cls.domain, 'Test App 2')
        cls.report_config2 = get_sample_report_config()
        cls.report_config2.domain = cls.domain
        cls.report_config2.save()
        report_app_config = {
            'report_id': cls.report_config2.get_id,
            'uuid': 'abcdef'
        }
        module = cls.app2.add_module(ReportModule.new_module('Reports', None))
        module.report_configs = [ReportAppConfig.wrap(report_app_config)]
        cls.app2.save()

        cls.app3 = Application.new_app(cls.domain, 'Test App 3')
        cls.app3.save()

    @classmethod
    def tearDownClass(cls):
        toggles.MOBILE_UCR.set(cls.domain, False, toggles.NAMESPACE_DOMAIN)
        cls.app1.delete()
        cls.report_config1.delete()
        cls.app2.delete()
        cls.report_config2.delete()
        delete_all_users()
        domain = Domain.get_by_name(cls.domain)
        domain.delete()

    def test_report_fixtures_provider_without_app(self):
        """
        ReportFixturesProvider should iterate all apps if app not given
        """
        from corehq.apps.userreports.reports.data_source import ConfigurableReportDataSource
        with patch.object(ConfigurableReportDataSource, 'get_data') as get_data_mock:
            get_data_mock.return_value = self.rows
            fixtures = report_fixture_generator(self.user, '2.0', None)
        reports = fixtures[0].findall('.//report')
        self.assertEqual(len(reports), 2)
        report_ids = {r.attrib.get('id') for r in reports}
        self.assertEqual(report_ids, {'123456', 'abcdef'})

    def test_report_fixtures_provider_with_app(self):
        """
        ReportFixturesProvider should not iterate all apps if app given
        """
        from corehq.apps.userreports.reports.data_source import ConfigurableReportDataSource
        with patch.object(ConfigurableReportDataSource, 'get_data') as get_data_mock:
            get_data_mock.return_value = self.rows
            fixtures = report_fixture_generator(self.user, '2.0', None, app=self.app1)
        reports = fixtures[0].findall('.//report')
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].attrib.get('id'), '123456')

    def test_report_fixtures_provider_with_app_that_doesnt_have_reports(self):
        from corehq.apps.userreports.reports.data_source import ConfigurableReportDataSource
        with patch.object(ConfigurableReportDataSource, 'get_data') as get_data_mock:
            get_data_mock.return_value = self.rows
            fixtures = report_fixture_generator(self.user, '2.0', None, app=self.app3)
        self.assertEqual(len(fixtures), 0)
