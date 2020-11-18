import inspect
import json
import uuid
from collections import Counter
from datetime import datetime
from io import StringIO

from django.contrib.admin.utils import NestedObjects
from django.core import serializers
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.test import SimpleTestCase, TestCase

from casexml.apps.case.mock import CaseFactory, CaseIndex, CaseStructure

from corehq.apps.commtrack.helpers import make_product
from corehq.apps.commtrack.tests.util import get_single_balance_block
from corehq.apps.domain.models import Domain
from corehq.apps.domain_migration_flags.models import DomainMigrationProgress
from corehq.apps.dump_reload.sql import SqlDataDumper, SqlDataLoader
from corehq.apps.dump_reload.sql.dump import (
    get_model_iterator_builders_to_dump,
    get_objects_to_dump,
)
from corehq.apps.dump_reload.sql.load import (
    DefaultDictWithKey,
    constraint_checks_deferred,
)
from corehq.apps.hqcase.utils import submit_case_blocks
from corehq.apps.products.models import SQLProduct
from corehq.apps.zapier.consts import EventTypes
from corehq.apps.zapier.models import ZapierSubscription
from corehq.apps.zapier.signals.receivers import (
    zapier_subscription_post_delete,
)
from corehq.blobs.models import BlobMeta
from corehq.form_processor.backends.sql.dbaccessors import LedgerAccessorSQL
from corehq.form_processor.interfaces.dbaccessors import (
    CaseAccessors,
    FormAccessors,
)
from corehq.form_processor.models import (
    CaseTransaction,
    CommCareCaseIndexSQL,
    CommCareCaseSQL,
    LedgerTransaction,
    LedgerValue,
    XFormInstanceSQL,
)
from corehq.form_processor.tests.utils import (
    FormProcessorTestUtils,
    create_form_for_test,
    use_sql_backend,
)
from corehq.messaging.scheduling.scheduling_partitioned.models import (
    AlertScheduleInstance,
)


class BaseDumpLoadTest(TestCase):
    @classmethod
    def setUpClass(cls):
        post_delete.disconnect(zapier_subscription_post_delete, sender=ZapierSubscription)
        super(BaseDumpLoadTest, cls).setUpClass()
        cls.domain_name = uuid.uuid4().hex
        cls.domain = Domain(name=cls.domain_name)
        cls.domain.save()

        cls.default_objects_counts = Counter({
            DomainMigrationProgress: 1
        })

    @classmethod
    def tearDownClass(cls):
        cls.domain.delete()
        super(BaseDumpLoadTest, cls).tearDownClass()
        post_delete.connect(zapier_subscription_post_delete, sender=ZapierSubscription)

    def delete_sql_data(self):
        for model_class, builder in get_model_iterator_builders_to_dump(self.domain_name, []):
            for iterator in builder.querysets():
                with transaction.atomic(using=iterator.db), \
                        constraint_checks_deferred(iterator.db):
                    collector = NestedObjects(using=iterator.db)
                    collector.collect(iterator)
                    collector.delete()

        self.assertEqual([], list(get_objects_to_dump(self.domain_name, [])))

    def tearDown(self):
        self.delete_sql_data()
        super(BaseDumpLoadTest, self).tearDown()

    def _dump_and_load(self, expected_dump_counts, load_filter=None, expected_load_counts=None):
        expected_load_counts = expected_load_counts or expected_dump_counts
        expected_dump_counts.update(self.default_objects_counts)

        models = list(expected_dump_counts)
        self._check_signals_handle_raw(models)

        output_stream = StringIO()
        SqlDataDumper(self.domain_name, []).dump(output_stream)

        self.delete_sql_data()

        # make sure that there's no data left in the DB
        objects_remaining = list(get_objects_to_dump(self.domain_name, []))
        object_classes = [obj.__class__.__name__ for obj in objects_remaining]
        counts = Counter(object_classes)
        self.assertEqual([], objects_remaining, 'Not all data deleted: {}'.format(counts))

        # Dump
        dump_output = output_stream.getvalue().split('\n')
        dump_lines = [line.strip() for line in dump_output if line.strip()]

        expected_model_counts = _normalize_object_counter(expected_dump_counts)
        actual_model_counts = Counter([json.loads(line)['model'] for line in dump_lines])
        self.assertDictEqual(dict(expected_model_counts), dict(actual_model_counts))

        # Load
        loader = SqlDataLoader(object_filter=load_filter)
        loaded_model_counts = loader.load_objects(dump_lines)

        normalized_expected_loaded_counts = _normalize_object_counter(expected_load_counts, for_loaded=True)
        self.assertDictEqual(dict(normalized_expected_loaded_counts), dict(loaded_model_counts))
        self.assertEqual(sum(expected_load_counts.values()), sum(loaded_model_counts.values()))

        return dump_lines

    def _check_signals_handle_raw(self, models):
        """Ensure that any post_save signal handlers have been updated
        to handle 'raw' calls."""
        whitelist_receivers = [
            'django_digest.models._post_save_persist_partial_digests'
        ]
        for model in models:
            for receiver in post_save._live_receivers(model):
                receiver_path = receiver.__module__ + '.' + receiver.__name__
                if receiver_path in whitelist_receivers:
                    continue
                args = inspect.getargspec(receiver).args
                message = 'Signal handler "{}" for model "{}" missing raw arg'.format(
                    receiver, model
                )
                self.assertIn('raw', args, message)


@use_sql_backend
class TestSQLDumpLoadShardedModels(BaseDumpLoadTest):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super(TestSQLDumpLoadShardedModels, cls).setUpClass()
        cls.factory = CaseFactory(domain=cls.domain_name)
        cls.form_accessors = FormAccessors(cls.domain_name)
        cls.case_accessors = CaseAccessors(cls.domain_name)
        cls.product = make_product(cls.domain_name, 'A Product', 'prodcode_a')
        cls.default_objects_counts.update({SQLProduct: 1})

    @classmethod
    def tearDownClass(cls):
        FormProcessorTestUtils.delete_all_cases_forms_ledgers(cls.domain_name)
        super(TestSQLDumpLoadShardedModels, cls).tearDownClass()

    def test_dump_load_form(self):
        expected_object_counts = Counter({
            XFormInstanceSQL: 2,
            BlobMeta: 2
        })

        pre_forms = [
            create_form_for_test(self.domain_name),
            create_form_for_test(self.domain_name)
        ]
        self._dump_and_load(expected_object_counts)

        form_ids = self.form_accessors.get_all_form_ids_in_domain('XFormInstance')
        self.assertEqual(set(form_ids), set(form.form_id for form in pre_forms))

        for pre_form in pre_forms:
            post_form = self.form_accessors.get_form(pre_form.form_id)
            self.assertDictEqual(pre_form.to_json(), post_form.to_json())

    def test_sql_dump_load_case(self):
        expected_object_counts = Counter({
            XFormInstanceSQL: 2,
            BlobMeta: 2,
            CommCareCaseSQL: 2,
            CaseTransaction: 3,
            CommCareCaseIndexSQL: 1

        })

        pre_cases = self.factory.create_or_update_case(
            CaseStructure(
                attrs={'case_name': 'child', 'update': {'age': 3, 'diabetic': False}, 'create': True},
                indices=[
                    CaseIndex(CaseStructure(attrs={'case_name': 'parent', 'update': {'age': 42}, 'create': True})),
                ]
            )
        )
        pre_cases[0] = self.factory.create_or_update_case(CaseStructure(
            case_id=pre_cases[0].case_id,
            attrs={'external_id': 'billie jean', 'update': {'name': 'Billie Jean'}}
        ))[0]

        self._dump_and_load(expected_object_counts)

        case_ids = self.case_accessors.get_case_ids_in_domain()
        self.assertEqual(set(case_ids), set(case.case_id for case in pre_cases))
        for pre_case in pre_cases:
            post_case = self.case_accessors.get_case(pre_case.case_id)
            self.assertDictEqual(pre_case.to_json(), post_case.to_json())

    def test_ledgers(self):
        expected_object_counts = Counter({
            XFormInstanceSQL: 3,
            BlobMeta: 3,
            CommCareCaseSQL: 1,
            CaseTransaction: 3,
            LedgerValue: 1,
            LedgerTransaction: 2

        })

        case = self.factory.create_case()
        submit_case_blocks([
            get_single_balance_block(case.case_id, self.product._id, 10)
        ], self.domain_name)
        submit_case_blocks([
            get_single_balance_block(case.case_id, self.product._id, 5)
        ], self.domain_name)

        pre_ledger_values = LedgerAccessorSQL.get_ledger_values_for_case(case.case_id)
        pre_ledger_transactions = LedgerAccessorSQL.get_ledger_transactions_for_case(case.case_id)
        self.assertEqual(1, len(pre_ledger_values))
        self.assertEqual(2, len(pre_ledger_transactions))

        self._dump_and_load(expected_object_counts)

        post_ledger_values = LedgerAccessorSQL.get_ledger_values_for_case(case.case_id)
        post_ledger_transactions = LedgerAccessorSQL.get_ledger_transactions_for_case(case.case_id)
        self.assertEqual(1, len(post_ledger_values))
        self.assertEqual(2, len(post_ledger_transactions))
        self.assertEqual(pre_ledger_values[0].ledger_reference, post_ledger_values[0].ledger_reference)
        self.assertDictEqual(pre_ledger_values[0].to_json(), post_ledger_values[0].to_json())

        pre_ledger_transactions = sorted(pre_ledger_transactions, key=lambda t: t.pk)
        post_ledger_transactions = sorted(post_ledger_transactions, key=lambda t: t.pk)
        for pre, post in zip(pre_ledger_transactions, post_ledger_transactions):
            self.assertEqual(str(pre), str(post))


class TestSQLDumpLoad(BaseDumpLoadTest):
    def assertModelsEqual(self, pre_models, post_models):
        for pre, post in zip(pre_models, post_models):
            pre_json = serializers.serialize('python', [pre])[0]
            post_json = serializers.serialize('python', [post])[0]
            self.assertDictEqual(pre_json, post_json)

    def test_case_search_config(self):
        from corehq.apps.case_search.models import CaseSearchConfig, FuzzyProperties
        expected_object_counts = Counter({
            CaseSearchConfig: 1,
            FuzzyProperties: 2,
        })

        pre_config, created = CaseSearchConfig.objects.get_or_create(pk=self.domain_name)
        pre_config.enabled = True
        pre_fuzzies = [
            FuzzyProperties(domain=self.domain, case_type='dog', properties=['breed', 'color']),
            FuzzyProperties(domain=self.domain, case_type='owner', properties=['name']),
        ]
        for fuzzy in pre_fuzzies:
            fuzzy.save()
        pre_config.fuzzy_properties.set(pre_fuzzies)
        pre_config.save()

        self._dump_and_load(expected_object_counts)

        post_config = CaseSearchConfig.objects.get(domain=self.domain_name)
        self.assertTrue(post_config.enabled)
        self.assertEqual(pre_config.fuzzy_properties, post_config.fuzzy_properties)
        post_fuzzies = FuzzyProperties.objects.filter(domain=self.domain_name)
        self.assertEqual(set(f.case_type for f in post_fuzzies), {'dog', 'owner'})

    def test_users(self):
        from corehq.apps.users.models import CommCareUser
        from corehq.apps.users.models import WebUser
        from django.contrib.auth.models import User

        expected_object_counts = Counter({User: 3})

        ccuser_1 = CommCareUser.create(
            domain=self.domain_name,
            username='user_1',
            password='secret',
            created_by=None,
            created_via=None,
            email='email@example.com',
        )
        ccuser_2 = CommCareUser.create(
            domain=self.domain_name,
            username='user_2',
            password='secret',
            created_by=None,
            created_via=None,
            email='email1@example.com',
        )
        web_user = WebUser.create(
            domain=self.domain_name,
            username='webuser_t1',
            password='secret',
            created_by=None,
            created_via=None,
            email='webuser@example.com',
        )
        self.addCleanup(ccuser_1.delete, deleted_by=None)
        self.addCleanup(ccuser_2.delete, deleted_by=None)
        self.addCleanup(web_user.delete, deleted_by=None)

        self._dump_and_load(expected_object_counts)

    def test_device_logs(self):
        from corehq.apps.receiverwrapper.util import submit_form_locally
        from phonelog.models import DeviceReportEntry, ForceCloseEntry, UserEntry, UserErrorEntry
        from corehq.apps.users.models import CommCareUser
        from django.contrib.auth.models import User

        expected_object_counts = Counter({
            User: 1,
            DeviceReportEntry: 7,
            UserEntry: 1,
            UserErrorEntry: 2,
            ForceCloseEntry: 1
        })

        user = CommCareUser.create(
            domain=self.domain_name,
            username='user_1',
            password='secret',
            created_by=None,
            created_via=None,
            email='email@example.com',
            uuid='428d454aa9abc74e1964e16d3565d6b6'  # match ID in devicelog.xml
        )
        self.addCleanup(user.delete, deleted_by=None)

        with open('corehq/ex-submodules/couchforms/tests/data/devicelogs/devicelog.xml', 'rb') as f:
            xml = f.read()
        submit_form_locally(xml, self.domain_name)

        self._dump_and_load(expected_object_counts)

    def test_demo_user_restore(self):
        from corehq.apps.users.models import CommCareUser
        from corehq.apps.ota.models import DemoUserRestore
        from django.contrib.auth.models import User

        expected_object_counts = Counter({
            User: 1,
            DemoUserRestore: 1
        })

        user_id = uuid.uuid4().hex
        user = CommCareUser.create(
            domain=self.domain_name,
            username='user_1',
            password='secret',
            created_by=None,
            created_via=None,
            email='email@example.com',
            uuid=user_id
        )
        self.addCleanup(user.delete, deleted_by=None)

        DemoUserRestore(
            demo_user_id=user_id,
            restore_blob_id=uuid.uuid4().hex,
            content_length=1027,
            restore_comment="Test migrate demo user restore"
        ).save()

        self._dump_and_load(expected_object_counts)

    def test_products(self):
        from corehq.apps.products.models import SQLProduct
        expected_object_counts = Counter({SQLProduct: 3})

        p1 = SQLProduct.objects.create(domain=self.domain_name, product_id='test1', name='test1')
        p2 = SQLProduct.objects.create(domain=self.domain_name, product_id='test2', name='test2')
        parchived = SQLProduct.objects.create(domain=self.domain_name, product_id='test3', name='test3', is_archived=True)

        self._dump_and_load(expected_object_counts)

        self.assertEqual(2, SQLProduct.active_objects.filter(domain=self.domain_name).count())
        all_active = SQLProduct.active_objects.filter(domain=self.domain_name).all()
        self.assertTrue(p1 in all_active)
        self.assertTrue(p2 in all_active)
        self.assertTrue(parchived not in all_active)

    def test_location_type(self):
        from corehq.apps.locations.models import LocationType
        from corehq.apps.locations.tests.test_location_types import make_loc_type
        expected_object_counts = Counter({LocationType: 7})

        state = make_loc_type('state', domain=self.domain_name)

        district = make_loc_type('district', state, domain=self.domain_name)
        section = make_loc_type('section', district, domain=self.domain_name)
        block = make_loc_type('block', district, domain=self.domain_name)
        center = make_loc_type('center', block, domain=self.domain_name)

        county = make_loc_type('county', state, domain=self.domain_name)
        city = make_loc_type('city', county, domain=self.domain_name)

        self._dump_and_load(expected_object_counts)

        hierarchy = LocationType.objects.full_hierarchy(self.domain_name)
        desired_hierarchy = {
            state.id: (
                state,
                {
                    district.id: (
                        district,
                        {
                            section.id: (section, {}),
                            block.id: (block, {
                                center.id: (center, {}),
                            }),
                        },
                    ),
                    county.id: (
                        county,
                        {city.id: (city, {})},
                    ),
                },
            ),
        }
        self.assertEqual(hierarchy, desired_hierarchy)

    def test_location(self):
        from corehq.apps.locations.models import LocationType, SQLLocation
        from corehq.apps.locations.tests.util import setup_locations_and_types
        expected_object_counts = Counter({LocationType: 3, SQLLocation: 11})

        location_type_names = ['province', 'district', 'city']
        location_structure = [
            ('Western Cape', [
                ('Cape Winelands', [
                    ('Stellenbosch', []),
                    ('Paarl', []),
                ]),
                ('Cape Town', [
                    ('Cape Town City', []),
                ])
            ]),
            ('Gauteng', [
                ('Ekurhuleni ', [
                    ('Alberton', []),
                    ('Benoni', []),
                    ('Springs', []),
                ]),
            ]),
        ]

        location_types, locations = setup_locations_and_types(
            self.domain_name,
            location_type_names,
            [],
            location_structure,
        )

        self._dump_and_load(expected_object_counts)

        names = ['Cape Winelands', 'Paarl', 'Cape Town']
        location_ids = [locations[name].location_id for name in names]
        result = SQLLocation.objects.get_locations_and_children(location_ids)
        self.assertItemsEqual(
            [loc.name for loc in result],
            ['Cape Winelands', 'Stellenbosch', 'Paarl', 'Cape Town', 'Cape Town City']
        )

        result = SQLLocation.objects.get_locations_and_children([locations['Gauteng'].location_id])
        self.assertItemsEqual(
            [loc.name for loc in result],
            ['Gauteng', 'Ekurhuleni ', 'Alberton', 'Benoni', 'Springs']
        )

    def test_sms(self):
        from corehq.apps.sms.models import PhoneNumber, MessagingEvent, MessagingSubEvent
        expected_object_counts = Counter({PhoneNumber: 1, MessagingEvent: 1, MessagingSubEvent: 1})

        phone_number = PhoneNumber(
            domain=self.domain_name,
            owner_doc_type='CommCareCase',
            owner_id='fake-owner-id1',
            phone_number='99912341234',
            backend_id=None,
            ivr_backend_id=None,
            verified=True,
            is_two_way=True,
            pending_verification=False,
            contact_last_modified=datetime.utcnow()
        )
        phone_number.save()
        event = MessagingEvent.objects.create(
            domain=self.domain_name,
            date=datetime.utcnow(),
            source=MessagingEvent.SOURCE_REMINDER,
            content_type=MessagingEvent.CONTENT_SMS,
            status=MessagingEvent.STATUS_COMPLETED
        )
        MessagingSubEvent.objects.create(
            parent=event,
            date=datetime.utcnow(),
            recipient_type=MessagingEvent.RECIPIENT_CASE,
            content_type=MessagingEvent.CONTENT_SMS,
            status=MessagingEvent.STATUS_COMPLETED
        )

        self._dump_and_load(expected_object_counts)

    def test_message_scheduling(self):
        AlertScheduleInstance(
            schedule_instance_id=uuid.uuid4(),
            domain=self.domain_name,
            recipient_type='CommCareUser',
            recipient_id=uuid.uuid4().hex,
            current_event_num=0,
            schedule_iteration_num=1,
            next_event_due=datetime(2017, 3, 1),
            active=True,
            alert_schedule_id=uuid.uuid4(),
        ).save()
        self._dump_and_load({AlertScheduleInstance: 1})

    def test_mobile_backend(self):
        from corehq.apps.sms.models import (
            SQLMobileBackend,
            SQLMobileBackendMapping,
        )

        domain_backend = SQLMobileBackend.objects.create(
            domain=self.domain_name,
            name='test-domain-mobile-backend',
            display_name='Test Domain Mobile Backend',
            hq_api_id='TDMB',
            inbound_api_key='test-domain-mobile-backend-inbound-api-key',
            supported_countries=["*"],
            backend_type=SQLMobileBackend.SMS,
            is_global=False,
        )
        SQLMobileBackendMapping.objects.create(
            domain=self.domain_name,
            backend=domain_backend,
            backend_type=SQLMobileBackend.SMS,
            prefix='123',
        )

        global_backend = SQLMobileBackend.objects.create(
            domain=None,
            name='test-global-mobile-backend',
            display_name='Test Global Mobile Backend',
            hq_api_id='TGMB',
            inbound_api_key='test-global-mobile-backend-inbound-api-key',
            supported_countries=["*"],
            backend_type=SQLMobileBackend.SMS,
            is_global=True,
        )
        SQLMobileBackendMapping.objects.create(
            domain=self.domain_name,
            backend=global_backend,
            backend_type=SQLMobileBackend.SMS,
            prefix='*',
        )
        self._dump_and_load({
            SQLMobileBackendMapping: 1,
            SQLMobileBackend: 1,
        })
        self.assertEqual(SQLMobileBackend.objects.first().domain,
                         self.domain_name)
        self.assertEqual(SQLMobileBackendMapping.objects.first().domain,
                         self.domain_name)

    def test_case_importer(self):
        from corehq.apps.case_importer.tracking.models import (
            CaseUploadFileMeta,
            CaseUploadFormRecord,
            CaseUploadRecord,
        )

        upload_file_meta = CaseUploadFileMeta.objects.create(
            identifier=uuid.uuid4().hex,
            filename='picture.jpg',
            length=1024,
        )
        case_upload_record = CaseUploadRecord.objects.create(
            domain=self.domain_name,
            upload_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            couch_user_id=uuid.uuid4().hex,
            case_type='person',
            upload_file_meta=upload_file_meta,
        )
        CaseUploadFormRecord.objects.create(
            case_upload_record=case_upload_record,
            form_id=uuid.uuid4().hex,
        )
        self._dump_and_load(Counter({
            CaseUploadFileMeta: 1,
            CaseUploadRecord: 1,
            CaseUploadFormRecord: 1,
        }))

    def test_transifex(self):
        from corehq.apps.translations.models import TransifexProject, TransifexOrganization
        org = TransifexOrganization.objects.create(slug='test', name='demo', api_token='123')
        TransifexProject.objects.create(
            organization=org, slug='testp', name='demop', domain=self.domain_name
        )
        self._dump_and_load(Counter({TransifexOrganization: 1, TransifexProject: 1}))

    def test_filtered_dump_load(self):
        from corehq.apps.locations.tests.test_location_types import make_loc_type
        from corehq.apps.products.models import SQLProduct
        from corehq.apps.locations.models import LocationType

        make_loc_type('state', domain=self.domain_name)
        SQLProduct.objects.create(domain=self.domain_name, product_id='test1', name='test1')
        expected_object_counts = Counter({LocationType: 1, SQLProduct: 1})

        self._dump_and_load(expected_object_counts, load_filter='sqlproduct', expected_load_counts=Counter({SQLProduct: 1}))
        self.assertEqual(0, LocationType.objects.count())

    def test_sms_content(self):
        from corehq.messaging.scheduling.models import AlertSchedule, SMSContent, AlertEvent
        from corehq.messaging.scheduling.scheduling_partitioned.dbaccessors import \
            delete_alert_schedule_instances_for_schedule

        schedule = AlertSchedule.create_simple_alert(self.domain, SMSContent())

        schedule.set_custom_alert(
            [
                (AlertEvent(minutes_to_wait=5), SMSContent()),
                (AlertEvent(minutes_to_wait=15), SMSContent()),
            ]
        )

        self.addCleanup(lambda: delete_alert_schedule_instances_for_schedule(AlertScheduleInstance, schedule.schedule_id))
        self._dump_and_load(Counter({AlertSchedule: 1, AlertEvent: 2, SMSContent: 2}))

    def test_zapier_subscription(self):
        ZapierSubscription.objects.create(
            domain=self.domain_name,
            case_type='case_type',
            event_name=EventTypes.NEW_CASE,
            url='example.com',
            user_id='user_id',
        )
        self._dump_and_load(Counter({ZapierSubscription: 1}))


class DefaultDictWithKeyTests(SimpleTestCase):

    def test_intended_use_case(self):
        def enlist(item):
            return [item]
        greasy_spoon = DefaultDictWithKey(enlist)
        self.assertEqual(greasy_spoon['spam'], ['spam'])
        greasy_spoon['spam'].append('spam')
        self.assertEqual(greasy_spoon['spam'], ['spam', 'spam'])

    def test_not_enough_params(self):
        def empty_list():
            return []
        greasy_spoon = DefaultDictWithKey(empty_list)
        with self.assertRaisesRegex(
            TypeError,
            r'empty_list\(\) takes 0 positional arguments but 1 was given'
        ):
            greasy_spoon['spam']

    def test_too_many_params(self):
        def appender(item1, item2):
            return [item1, item2]
        greasy_spoon = DefaultDictWithKey(appender)
        with self.assertRaisesRegex(
            TypeError,
            r"appender\(\) missing 1 required positional argument: 'item2'"
        ):
            greasy_spoon['spam']

    def test_no_factory(self):
        greasy_spoon = DefaultDictWithKey()
        with self.assertRaisesRegex(
            TypeError,
            "'NoneType' object is not callable"
        ):
            greasy_spoon['spam']


def _normalize_object_counter(counter, for_loaded=False):
    """Converts a <Model Class> keyed counter to an model label keyed counter"""
    def _model_class_to_label(model_class):
        label = '{}.{}'.format(model_class._meta.app_label, model_class.__name__)
        return label if for_loaded else label.lower()
    return Counter({
        _model_class_to_label(model_class): count
        for model_class, count in counter.items()
    })
