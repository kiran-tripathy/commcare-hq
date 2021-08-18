from corehq.messaging.smsbackends.telerivet.models import SQLTelerivetBackend
from corehq.apps.sms.models import SMS
from django.test import TestCase
from django.urls import reverse


class TelerivetViewTestCase(TestCase):

    view_path = 'telerivet_message_status'

    def setUp(self):
        self.backend = SQLTelerivetBackend(
            name='TELERIVET',
            is_global=True,
            hq_api_id=SQLTelerivetBackend.get_api_id()
        )
        self.backend.set_extra_fields(
            webhook_secret='The chamber of webhook secrets'
        )
        self.backend.save()

        self.sms = SMS(
            phone_number='27845698785',
            text="Fame is fickle"
        )
        self.sms.save()

    def tearDown(self):
        self.backend.delete()
        self.sms.delete()

    def test_message_status_successful_without_prior_metadata(self):
        data = {'status': 'delivered', 'vars[case_id]': '123321', 'secret': self.backend.config.webhook_secret}
        response = self.client.post(reverse(self.view_path, kwargs={'message_id': self.sms.couch_id}), data)

        self.assertTrue(response.status_code, 200)
        self.sms.refresh_from_db()

        expected_custom_metadata = {'gateway_delivered': True, 'case_id': '123321'}
        self.assertEqual(self.sms.custom_metadata, expected_custom_metadata)

    def test_message_status_successful_with_metadata(self):
        self.sms.custom_metadata = {'custom': 'data'}
        self.sms.save()

        data = {'status': 'delivered', 'vars[case_id]': '123321', 'secret': self.backend.config.webhook_secret}
        response = self.client.post(reverse(self.view_path, kwargs={'message_id': self.sms.couch_id}), data)

        self.assertTrue(response.status_code, 200)
        self.sms.refresh_from_db()

        expected_custom_metadata = {
            'custom': 'data',
            'gateway_delivered': True,
            'case_id': '123321'
        }
        self.assertEqual(self.sms.custom_metadata, expected_custom_metadata)

    def test_message_status_with_wrong_message_id(self):
        self.sms.custom_metadata = {}
        self.sms.save()

        data = {'status': 'delivered', 'vars[case_id]': '123321', 'secret': self.backend.config.webhook_secret}
        response = self.client.post(reverse(self.view_path, kwargs={'message_id': '0987654321a'}), data)

        self.assertTrue(response.status_code, 200)
        self.sms.refresh_from_db()
        self.assertEqual(self.sms.custom_metadata, {})
