from django.test import TestCase
from django.urls import reverse

from corehq.apps.domain.models import Domain
from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.domain.tests.test_views import BaseAutocompleteTest
from corehq.apps.hqwebapp.models import Alert
from corehq.apps.users.dbaccessors import delete_all_users
from corehq.apps.users.models import CommCareUser, WebUser


class TestEmailAuthenticationFormAutocomplete(BaseAutocompleteTest):

    def test_autocomplete_enabled(self):
        self.verify(True, reverse("login"), "auth-username")

    def test_autocomplete_disabled(self):
        self.verify(False, reverse("login"), "auth-username")


class TestBugReport(TestCase):
    domain = 'test-bug-report'

    @classmethod
    def setUpClass(cls):
        super(TestBugReport, cls).setUpClass()
        delete_all_users()
        cls.project = create_domain(cls.domain)
        cls.web_user = WebUser.create(
            cls.domain,
            'bug-dude',
            password='***',
            created_by=None,
            created_via=None,
        )
        cls.web_user.is_superuser = True
        cls.web_user.save()
        cls.commcare_user = CommCareUser.create(
            cls.domain,
            'bug-kid',
            password='***',
            created_by=None,
            created_via=None,
        )
        cls.url = reverse("bug_report")

    @classmethod
    def tearDownClass(cls):
        delete_all_users()
        cls.project.delete()
        super(TestBugReport, cls).tearDownClass()

    def _default_payload(self, username):
        return {
            'subject': 'Bug',
            'username': username,
            'domain': self.domain,
            'url': 'www.bugs.com',
            'message': 'CommCare is broken, help!',
            'app_id': '',
            'cc': '',
            'email': '',
            '500traceback': '',
            'sentry_event_id': '',
        }

    def _post_bug_report(self, payload):
        return self.client.post(
            self.url,
            payload,
            HTTP_USER_AGENT='firefox',
        )

    def test_basic_bug_submit(self):
        self.client.login(username=self.web_user.username, password='***')

        payload = self._default_payload(self.web_user.username)

        response = self._post_bug_report(payload)
        self.assertEqual(response.status_code, 200)

    def test_project_description_web_user(self):
        self.client.login(username=self.web_user.username, password='***')

        payload = self._default_payload(self.web_user.username)
        payload.update({
            'project_description': 'Great NGO, Just Great',
        })

        domain_object = Domain.get_by_name(self.domain)
        self.assertIsNone(domain_object.project_description)

        response = self._post_bug_report(payload)
        self.assertEqual(response.status_code, 200)
        domain_object = Domain.get_by_name(self.domain)
        self.assertEqual(domain_object.project_description, 'Great NGO, Just Great')

        # Don't update if they've made it blank
        payload.update({
            'project_description': '',
        })
        response = self._post_bug_report(payload)
        self.assertEqual(response.status_code, 200)
        domain_object = Domain.get_by_name(self.domain)
        self.assertEqual(domain_object.project_description, 'Great NGO, Just Great')

    def test_project_description_commcare_user(self):
        self.client.login(username=self.commcare_user.username, password='***')

        payload = self._default_payload(self.commcare_user.username)
        payload.update({
            'project_description': 'Great NGO, Just Great',
        })

        domain_object = Domain.get_by_name(self.domain)
        self.assertIsNone(domain_object.project_description)

        response = self._post_bug_report(payload)
        self.assertEqual(response.status_code, 200)
        domain_object = Domain.get_by_name(self.domain)

        # Shouldn't be able to update description as commcare user
        self.assertIsNone(domain_object.project_description)


class TestMaintenanceAlertsView(TestCase):
    domain = 'maintenance-domain'

    @classmethod
    def setUpClass(cls):
        super(TestMaintenanceAlertsView, cls).setUpClass()
        cls.project = create_domain(cls.domain)
        cls.user = WebUser.create(
            cls.domain,
            'maintenance-user',
            password='***',
            created_by=None,
            created_via=None
        )
        cls.user.is_superuser = True
        cls.user.save()

    @classmethod
    def tearDownClass(cls):
        cls.user.delete(cls.domain, deleted_by=None)
        cls.project.delete()

    def _alert_with_timezone(self):
        self.client.login(username=self.user.username, password='***')
        params = {
            'alert_text': "Maintenance alert",
            'start_time': '2002-11-12T09:00:00',
            'end_time': '2002-11-12T17:00:00',
            'timezone': 'US/Eastern'
        }
        self.client.post(reverse('create_alert'), params)
        return Alert.objects.latest('created')

    def test_create_alert(self):
        self.client.login(username=self.user.username, password='***')
        self.assertEqual(Alert.objects.count(), 0)

        self.client.post(reverse('create_alert'), {'alert_text': "Maintenance alert"})
        alert = Alert.objects.first()

        self.assertEqual(alert.text, 'Maintenance alert')
        self.assertIsNone(alert.domains)

    def test_create_converts_to_utc(self):
        alert = self._alert_with_timezone()

        # saves UTC-adjusted to database
        self.assertEqual(alert.start_time.isoformat(), '2002-11-12T14:00:00')
        self.assertEqual(alert.end_time.isoformat(), '2002-11-12T22:00:00')

    def test_view_converts_from_utc(self):
        self._alert_with_timezone()
        response = self.client.get(reverse('alerts'))
        alert = response.context['alerts'][0]

        # displays timezone-adjusted to user
        self.assertEqual(alert['start_time'], 'Nov 12, 2002 09:00 EST')
        self.assertEqual(alert['end_time'], 'Nov 12, 2002 17:00 EST')

    def test_post_commands(self):
        self.client.login(username=self.user.username, password='***')
        self.client.post(reverse('create_alert'), {'alert_text': "Maintenance alert"})
        alert = Alert.objects.latest('created')
        self.assertFalse(alert.active)

        self.client.post(reverse('alerts'), {'command': 'activate', 'alert_id': alert.id})
        alert = Alert.objects.get(id=alert.id)
        self.assertTrue(alert.active)

        self.client.post(reverse('alerts'), {'command': 'deactivate', 'alert_id': alert.id})
        alert = Alert.objects.get(id=alert.id)
        self.assertFalse(alert.active)

    def test_view_access_to_global_alerts_only(self):
        global_alert = Alert.objects.create(text='Test!', domains=['test1', 'test2'])
        self.addCleanup(global_alert.delete)

        domain_alert = Alert.objects.create(created_by_domain='dummy_domain')
        self.addCleanup(domain_alert.delete)
        assert domain_alert.pk

        self.client.login(username=self.user.username, password='***')
        response = self.client.get(reverse('alerts'))

        self.assertListEqual(
            response.context['alerts'],
            [{
                'active': False,
                'created': str(global_alert.created),
                'domains': 'test1, test2',
                'end_time': None,
                'expired': None,
                'html': 'Test!',
                'id': global_alert.id,
                'start_time': None

            }]
        )

    def test_update_restricted_to_global_alerts(self):
        domain_alert = Alert.objects.create(created_by_domain='dummy_domain')
        self.addCleanup(domain_alert.delete)

        self.client.login(username=self.user.username, password='***')
        with self.assertRaisesMessage(Alert.DoesNotExist,
                                      'Alert matching query does not exist'):
            self.client.post(reverse('alerts'), {'command': 'activate', 'alert_id': domain_alert.id})
