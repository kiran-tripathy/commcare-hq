import uuid
from datetime import datetime

from django.test import TestCase
from contextlib import contextmanager
from casexml.apps.case.mock import CaseFactory, CaseBlock

from corehq.apps.export.const import DEID_ID_TRANSFORM, DEID_DATE_TRANSFORM
from corehq.apps.hqcase.utils import (
    get_case_value,
    get_deidentified_data,
    submit_case_blocks,
)
from corehq.apps.hqcase.case_deletion_utils import get_ordered_case_xforms
from corehq.apps.reports.tests.test_case_data import _delete_all_cases_and_forms
from corehq.form_processor.models import CommCareCase

DOMAIN = 'test-domain'


class TestGetCaseValue(TestCase):

    def test_value_is_case_attribute(self):
        attr_value = 'external_id'
        attr = 'external_id'

        with get_case(**{attr: attr_value}) as case:
            case_value, is_property = get_case_value(case, attr)

        self.assertFalse(is_property)
        self.assertEqual(case_value, attr_value)

    def test_value_is_case_property(self):
        properties = {
            'captain': 'Jack Sparrow'
        }

        with get_case(update=properties) as case:
            case_value, is_property = get_case_value(case, 'captain')

        self.assertTrue(is_property)
        self.assertEqual(case_value, 'Jack Sparrow')

    def test_value_does_not_exist(self):
        with get_case() as case:
            case_value, is_property = get_case_value(case, 'non-existing-property')

        self.assertTrue(case_value is None)
        self.assertTrue(is_property is None)

    def test_no_value_provided_results_in_none(self):
        with get_case() as case:
            case_value, is_property = get_case_value(case, '')

        self.assertTrue(case_value is None)
        self.assertTrue(is_property is None)


class TestGetCensoredCaseData(TestCase):

    def test_no_censor_data_provided(self):
        with get_case() as case:
            censored_attrs, censored_props = get_deidentified_data(case, {})

        self.assertTrue(censored_attrs == censored_props == {})

    def test_valid_attributes_and_properties(self):
        properties = {
            'captain': 'Jack Sparrow',
        }
        attrs = {
            'external_id': 'external_id',
            'date_opened': str(datetime.utcnow()),
        }
        censor_data = {
            'date_opened': DEID_DATE_TRANSFORM,
            'captain': DEID_ID_TRANSFORM,
        }
        with get_case(update=properties, **attrs) as case:
            censored_attrs, censored_props = get_deidentified_data(case, censor_data)

        self.assertTrue(properties['captain'] != censored_props['captain'])
        self.assertTrue(attrs['date_opened'] != censored_attrs['date_opened'])

    def test_missing_properties(self):
        censor_data = {
            'captain': DEID_ID_TRANSFORM,
        }
        with get_case() as case:
            censored_attrs, censored_props = get_deidentified_data(case, censor_data)

        self.assertTrue(censored_attrs == censored_props == {})

    def test_invalid_deid_transform_blanks_property(self):
        properties = {
            'captain': 'Jack Sparrow',
        }
        censor_data = {
            'captain': 'invalid_deid_transform',
        }
        with get_case(update=properties) as case:
            censored_attrs, censored_props = get_deidentified_data(case, censor_data)

        self.assertTrue(censored_attrs == {})
        self.assertTrue(censored_props['captain'] == '')


class TestCaseDeletionUtil(TestCase):

    def test_xform_order(self):
        main_case_id = uuid.uuid4().hex
        child_case1_id = uuid.uuid4().hex
        child_case2_id = uuid.uuid4().hex
        child_case3_id = uuid.uuid4().hex
        submit_case_blocks([
            CaseBlock(main_case_id, case_name="main_case", create=True).as_text(),
            CaseBlock(child_case1_id, case_name="child1", create=True).as_text(),
        ], DOMAIN)
        submit_case_blocks([
            CaseBlock(main_case_id, update={}).as_text(),
            CaseBlock(child_case2_id, case_name="child2", create=True).as_text(),
        ], DOMAIN)
        submit_case_blocks([
            CaseBlock(main_case_id, update={}).as_text(),
            CaseBlock(child_case3_id, case_name="child3", create=True).as_text(),
        ], DOMAIN)
        self.addCleanup(_delete_all_cases_and_forms, DOMAIN)

        main_case = CommCareCase.objects.get_case(main_case_id, DOMAIN)
        xforms = get_ordered_case_xforms(main_case, DOMAIN)

        for xform in xforms:
            self.assertEqual(xforms.count(xform), 1)

        for i in range(2):
            self.assertGreater(xforms[i + 1].received_on, xforms[i].received_on)


@contextmanager
def get_case(*args, **kwargs):
    factory = CaseFactory(DOMAIN)
    case = factory.create_case(
        case_type='ship',
        case_name='Black Pearl',
        **kwargs,
    )
    try:
        yield case
    finally:
        factory.close_case(case.case_id)
