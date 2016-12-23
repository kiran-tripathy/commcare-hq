import json
from datetime import datetime
from django.test import TestCase

from corehq.form_processor.interfaces.dbaccessors import CaseAccessors
from corehq.util.test_utils import flag_enabled
from custom.enikshay.integrations.nikshay.repeaters import NikshayRegisterPatientRepeater
from custom.enikshay.tests.utils import ENikshayCaseStructureMixin

from custom.enikshay.integrations.nikshay.repeater_generator import NikshayRegisterPatientPayloadGenerator, \
    ENIKSHAY_ID
from corehq.form_processor.tests.utils import run_with_all_backends
from casexml.apps.case.mock import CaseStructure
from corehq.apps.repeaters.models import RepeatRecord
from corehq.apps.repeaters.dbaccessors import delete_all_repeat_records, delete_all_repeaters
from casexml.apps.case.tests.util import delete_all_cases


class MockResponse(object):
    def __init__(self, status_code, json_data):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


class NikshayRepeaterTestBase(ENikshayCaseStructureMixin, TestCase):
    def setUp(self):
        super(NikshayRepeaterTestBase, self).setUp()

        delete_all_repeat_records()
        delete_all_repeaters()
        delete_all_cases()

    def tearDown(self):
        super(NikshayRepeaterTestBase, self).tearDown()

        delete_all_repeat_records()
        delete_all_repeaters()
        delete_all_cases()

    def repeat_records(self):
        return RepeatRecord.all(domain=self.domain, due_before=datetime.utcnow())

    def _create_nikshay_enabled_case(self):
        nikshay_enabled_case_on_update = CaseStructure(
            case_id=self.episode_id,
            attrs={
                'case_type': 'episode',
                "update": dict(
                    episode_pending_registration='no',
                )
            }
        )

        return self.create_case(nikshay_enabled_case_on_update)[0]

    def _create_nikshay_registered_case(self):
        nikshay_registered_case = CaseStructure(
            case_id=self.episode_id,
            attrs={
                'create': True,
                'case_type': 'episode',
                "update": dict(
                    nikshay_registered='true',
                )
            }
        )
        self.create_case(nikshay_registered_case)


class TestNikshayRegisterPatientRepeater(NikshayRepeaterTestBase):

    def setUp(self):
        super(TestNikshayRegisterPatientRepeater, self).setUp()

        self.repeater = NikshayRegisterPatientRepeater(
            domain=self.domain,
            url='case-repeater-url',
            username='test-user'
        )
        self.repeater.white_listed_case_types = ['episode']
        self.repeater.save()

    def test_not_available_for_domain(self):
        self.assertFalse(NikshayRegisterPatientRepeater.available_for_domain(self.domain))

    @flag_enabled('NIKSHAY_INTEGRATION')
    def test_available_for_domain(self):
        self.assertTrue(NikshayRegisterPatientRepeater.available_for_domain(self.domain))

    @run_with_all_backends
    def test_trigger(self):
        # nikshay not enabled
        self.create_case(self.episode)
        self.assertEqual(0, len(self.repeat_records().all()))

        # nikshay enabled, should register a repeat record
        self._create_nikshay_enabled_case()
        self.assertEqual(1, len(self.repeat_records().all()))
        #
        # set as registered, should not register a new repeat record
        self._create_nikshay_registered_case()
        self.assertEqual(1, len(self.repeat_records().all()))


class TestNikshayRegisterPatientPayloadGenerator(NikshayRepeaterTestBase):
    def setUp(self):
        super(TestNikshayRegisterPatientPayloadGenerator, self).setUp()
        self.cases = self.create_case_structure()

    @run_with_all_backends
    def test_payload_general_properties(self):
        episode_case = self._create_nikshay_enabled_case()
        payload = (json.loads(
            NikshayRegisterPatientPayloadGenerator(None)
            .get_payload(None, episode_case))
        )
        self.assertEqual(payload['Source'], ENIKSHAY_ID)
        self.assertEqual(payload['Local_ID'], self.person_id)
        self.assertEqual(payload['regBy'], self.cases[self.person_id].owner_id)

    @run_with_all_backends
    def test_payload_person_properties(self):
        episode_case = self._create_nikshay_enabled_case()
        payload = (json.loads(
            NikshayRegisterPatientPayloadGenerator(None).get_payload(None, episode_case))
        )
        self.assertEqual(payload['pname'], "Pippin")
        self.assertEqual(payload['page'], '20')
        self.assertEqual(payload['pgender'], 'M')
        self.assertEqual(payload['paddress'], 'Mr. Everest')
        self.assertEqual(payload['pmob'], self.primary_phone_number)
        self.assertEqual(payload['cname'], 'Mrs. Everestie')
        self.assertEqual(payload['caddress'], 'Mrs. Everestie')
        self.assertEqual(payload['cmob'], self.secondary_phone_number)
        self.assertEqual(payload['pcategory'], '2')

    @run_with_all_backends
    def test_payload_episode_properties(self):
        episode_case = self._create_nikshay_enabled_case()
        payload = (json.loads(
            NikshayRegisterPatientPayloadGenerator(None).get_payload(None, episode_case))
        )
        self.assertEqual(payload['sitedetail'], 2)
        self.assertEqual(payload['Ptype'], '6')
        self.assertEqual(payload['poccupation'], 4)
        self.assertEqual(payload['dotname'], 'awesome dot')
        self.assertEqual(payload['dotmob'], '123456789')
        self.assertEqual(payload['disease_classification'], 'EP')
        self.assertEqual(payload['pregdate'], '2014-09-09')
        self.assertEqual(payload['ptbyr'], '2014')
        self.assertEqual(payload['dotpType'], '5')
        self.assertEqual(payload['dotdesignation'], 'ngo_volunteer')
        self.assertEqual(payload['dateofInitiation'], '2015-03-03')

    def _assert_case_property_equal(self, case, case_property, expected_value):
        self.assertEqual(case.dynamic_case_properties().get(case_property), expected_value)

    @run_with_all_backends
    def test_handle_success(self):
        nikshay_id = "NIKSHAY!"
        self._create_nikshay_enabled_case()
        payload_generator = NikshayRegisterPatientPayloadGenerator(None)
        payload_generator.handle_success(
            MockResponse(
                201,
                {
                    "Nikshay_Message": "Success",
                    "Results": [
                        {
                            "FieldName": "NikshayId",
                            "Fieldvalue": nikshay_id,
                        }
                    ]
                }
            ),
            self.cases[self.episode_id],
            None,
        )
        updated_episode_case = CaseAccessors(self.domain).get_case(self.episode_id)
        self._assert_case_property_equal(updated_episode_case, 'nikshay_registered', 'true')
        self._assert_case_property_equal(updated_episode_case, 'nikshay_error', '')
        self._assert_case_property_equal(updated_episode_case, 'nikshay_id', nikshay_id)
        self.assertEqual(updated_episode_case.external_id, nikshay_id)

    @run_with_all_backends
    def test_handle_bad_nikshay_response(self):
        self._create_nikshay_enabled_case()
        payload_generator = NikshayRegisterPatientPayloadGenerator(None)
        response = {
            "Nikshay_Message": "Success",
            "Results": [
                {
                    "FieldName": "BadResponse",
                    "Fieldvalue": "Borked",
                }
            ]
        }
        payload_generator.handle_success(
            MockResponse(
                201,
                response,
            ),
            self.cases[self.episode_id],
            None,
        )
        updated_episode_case = CaseAccessors(self.domain).get_case(self.episode_id)
        self._assert_case_property_equal(updated_episode_case, 'nikshay_registered', 'false')
        self._assert_case_property_equal(
            updated_episode_case,
            'nikshay_error',
            'No Nikshay ID received: {}'.format(response)
        )
