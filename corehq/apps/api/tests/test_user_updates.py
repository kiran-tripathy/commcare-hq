from django.test import TestCase
from django.core.exceptions import ValidationError

from corehq.apps.api.exceptions import UpdateUserException
from corehq.apps.api.user_updates import CommcareUserUpdates
from corehq.apps.custom_data_fields.models import (
    PROFILE_SLUG,
    CustomDataFieldsDefinition,
    CustomDataFieldsProfile,
    Field,
)
from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.groups.models import Group
from corehq.apps.locations.models import LocationType, SQLLocation
from corehq.apps.user_importer.helpers import UserChangeLogger
from corehq.apps.users.audit.change_messages import (
    GROUPS_FIELD,
    LOCATION_FIELD,
    PASSWORD_FIELD,
    ROLE_FIELD,
)
from corehq.apps.users.models import CommCareUser, HqPermissions
from corehq.apps.users.models_role import UserRole
from corehq.apps.users.views.mobile.custom_data_fields import UserFieldsView
from corehq.const import USER_CHANGE_VIA_API


class TestUpdateUserMethods(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.domain = 'test-domain'
        cls.domain_obj = create_domain(cls.domain)
        cls.addClassCleanup(cls.domain_obj.delete)
        cls.loc_type = LocationType.objects.create(domain=cls.domain, name='loc_type')
        cls.loc1 = SQLLocation.objects.create(
            location_id='loc1', location_type=cls.loc_type, domain=cls.domain)
        cls.loc2 = SQLLocation.objects.create(
            location_id='loc2', location_type=cls.loc_type, domain=cls.domain)

    def setUp(self) -> None:
        super().setUp()
        self.user = CommCareUser.create('test-domain', 'test-username', 'qwer1234', None, None)
        self.addCleanup(self.user.delete, self.domain, deleted_by=None)
        self.commcare_user_updater = CommcareUserUpdates(self.user, self.domain)

    def test_update_password_without_strong_passwords_succeeds(self):
        self.domain_obj.strong_mobile_passwords = False
        self.domain_obj.save()

        self.commcare_user_updater.update('password', 'abc123')  # should not raise

    def test_update_password_with_strong_passwords_raises_exception(self):
        self.domain_obj.strong_mobile_passwords = True
        self.domain_obj.save()

        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('password', 'abc123')

        self.assertEqual(cm.exception.message, "Password is not strong enough.")

    def test_update_password_with_strong_passwords_succeeds(self):
        self.domain_obj.strong_mobile_passwords = True
        self.domain_obj.save()

        self.commcare_user_updater.update('password', 'a7d8fhjkdf8d')  # should not raise

    def test_update_email_succeeds(self):
        self.user.email = 'initial@dimagi.com'
        self.commcare_user_updater.update('email', 'updated@dimagi.com')
        self.assertEqual(self.user.email, 'updated@dimagi.com')

    def test_update_first_name_succeeds(self):
        self.user.first_name = 'Initial'
        self.commcare_user_updater.update('first_name', 'Updated')
        self.assertEqual(self.user.first_name, 'Updated')

    def test_update_last_name_succeeds(self):
        self.user.last_name = 'Initial'
        self.commcare_user_updater.update('last_name', 'Updated')
        self.assertEqual(self.user.last_name, 'Updated')

    def test_update_language_succeeds(self):
        self.user.language = 'in'
        self.commcare_user_updater.update('language', 'up')
        self.assertEqual(self.user.language, 'up')

    def test_update_default_phone_number_succeeds(self):
        self.user.set_default_phone_number('50253311398')
        self.commcare_user_updater.update('default_phone_number', '50253311399')
        self.assertEqual(self.user.default_phone_number, '50253311399')

    def test_update_default_phone_number_preserves_previous_number(self):
        self.user.set_default_phone_number('50253311398')
        self.commcare_user_updater.update('default_phone_number', '50253311399')
        self.assertIn('50253311398', self.user.phone_numbers)

    def test_update_default_phone_number_raises_exception_if_not_string(self):
        self.user.set_default_phone_number('50253311398')
        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('default_phone_number', 50253311399)

        self.assertEqual(cm.exception.message, "'default_phone_number' must be a string")

    def test_update_phone_numbers_succeeds(self):
        self.user.phone_numbers = ['50253311398']
        self.commcare_user_updater.update('phone_numbers', ['50253311399', '50253311398'])
        self.assertEqual(self.user.phone_numbers, ['50253311399', '50253311398'])

    def test_update_phone_numbers_updates_default(self):
        self.user.set_default_phone_number('50253311398')
        self.commcare_user_updater.update('phone_numbers', ['50253311399', '50253311398'])
        self.assertEqual(self.user.default_phone_number, '50253311399')

    def test_update_user_data_succeeds(self):
        self.user.get_user_data(self.domain)['custom_data'] = "initial custom data"
        self.commcare_user_updater.update('user_data', {'custom_data': 'updated custom data'})
        self.assertEqual(self.user.get_user_data(self.domain)["custom_data"], "updated custom data")

    def test_update_user_data_raises_exception_if_profile_conflict(self):
        profile_id = self._setup_profile()
        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('user_data', {PROFILE_SLUG: profile_id, 'conflicting_field': 'no'})
        self.assertEqual(cm.exception.message, "'conflicting_field' cannot be set directly")

    def test_profile_not_found(self):
        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('user_data', {PROFILE_SLUG: 123456})
        self.assertEqual(cm.exception.message, "User data profile not found")

    def test_validation_error_when_profile_required(self):
        self.definition = CustomDataFieldsDefinition.get_or_create(self.domain, UserFieldsView.field_type)
        self.definition.profile_required_for_user_type = [UserFieldsView.COMMCARE_USER]
        self.definition.save()
        expected_error_message = "A profile assignment is required for Mobile Workers."
        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('user_data', {'custom_data': 'updated custom data'})
        self.assertEqual(cm.exception.message, expected_error_message)

    def test_no_validation_error_when_profile_required_and_provided(self):
        profile_id = self._setup_profile()
        self.definition = CustomDataFieldsDefinition.get_or_create(self.domain, UserFieldsView.field_type)
        self.definition.profile_required_for_user_type = [UserFieldsView.COMMCARE_USER]
        self.definition.save()
        self.commcare_user_updater.update('user_data', {PROFILE_SLUG: profile_id})

    def test_update_groups_succeeds(self):
        group = Group({"name": "test", "domain": self.user.domain})
        group.save()
        self.addCleanup(group.delete)
        self.commcare_user_updater.update('groups', [group._id])
        self.assertEqual(self.user.get_group_ids()[0], group._id)

    def test_update_groups_fails(self):
        group = Group({"name": "test", "domain": "not-same-domain"})
        group.save()
        self.addCleanup(group.delete)
        with self.assertRaises(ValidationError):
            self.commcare_user_updater.update('groups', [group._id])

    def test_update_groups_with_fake_group_id_raises_exception(self):
        with self.assertRaises(ValidationError):
            self.commcare_user_updater.update('groups', ["fake_id"])

    def test_update_unknown_field_raises_exception(self):
        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('username', 'new-username')

        self.assertEqual(cm.exception.message, "Attempted to update unknown or non-editable field 'username'")

    def test_update_user_role_succeeds(self):
        new_role = UserRole.create(
            self.domain, 'edit-data', permissions=HqPermissions(edit_data=True)
        )
        self.commcare_user_updater.update('role', 'edit-data')
        self.assertEqual(self.user.get_role(self.domain).get_qualified_id(), new_role.get_qualified_id())

    def test_update_user_role_raises_exception_if_does_not_exist(self):
        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('role', 'edit-data')

        self.assertEqual(cm.exception.message, "The role 'edit-data' does not exist")

    def test_update_user_role_raises_exception_if_ambiguous(self):
        UserRole.create(
            self.domain, 'edit-data', permissions=HqPermissions(edit_data=True)
        )
        UserRole.create(
            self.domain, 'edit-data', permissions=HqPermissions(edit_data=True)
        )

        with self.assertRaises(UpdateUserException) as cm:
            self.commcare_user_updater.update('role', 'edit-data')

        self.assertEqual(
            cm.exception.message,
            "There are multiple roles with the name 'edit-data' in the domain 'test-domain'"
        )

    def _setup_profile(self):
        self.definition = CustomDataFieldsDefinition(domain=self.domain,
                                                field_type=UserFieldsView.field_type)
        self.definition.save()
        self.definition.set_fields([
            Field(
                slug='conflicting_field',
                label='Conflicting Field',
                choices=['yes', 'no'],
            ),
        ])
        self.definition.save()
        profile = CustomDataFieldsProfile(
            name='character',
            fields={'conflicting_field': 'yes'},
            definition=self.definition,
        )
        profile.save()
        return profile.id

    def test_update_locations_raises_if_primary_location_not_in_location_list(self):
        with self.assertRaises(UpdateUserException) as e:
            self.commcare_user_updater.update('location',
                   {'primary_location': self.loc2.location_id, 'locations': [self.loc1.location_id]})

        self.assertEqual(str(e.exception), 'Primary location must be included in the list of locations.')

    def test_update_locations_raises_if_any_location_does_not_exist(self):
        with self.assertRaises(UpdateUserException) as e:
            self.commcare_user_updater.update('location',
                   {'primary_location': 'fake_loc', 'locations': [self.loc1.location_id, 'fake_loc']})
        self.assertEqual(str(e.exception), "Could not find location ids: fake_loc.")

    def test_update_locations_raises_if_primary_location_not_provided(self):
        with self.assertRaises(UpdateUserException) as e:
            self.commcare_user_updater.update('location', {'locations': [self.loc1.location_id]})
        self.assertEqual(str(e.exception), 'Both primary_location and locations must be provided together.')

    def test_update_locations_raises_if_locations_not_provided(self):
        with self.assertRaises(UpdateUserException) as e:
            self.commcare_user_updater.update('location', {'primary_location': self.loc1.location_id})
        self.assertEqual(str(e.exception), 'Both primary_location and locations must be provided together.')

    def test_update_locations_do_nothing_if_nothing_provided(self):
        self.user.set_location(self.loc1)
        self.commcare_user_updater.update('location', {'primary_location': None, 'locations': None})
        self.assertEqual(self.user.get_location_ids(self.domain), [self.loc1.location_id])
        self.assertEqual(self.user.get_location_id(self.domain), self.loc1.location_id)

    def test_update_locations_removes_locations_if_empty_string_provided(self):
        self.user.set_location(self.loc1)
        self.commcare_user_updater.update('location', {'primary_location': '', 'locations': []})
        self.assertEqual(self.user.get_location_ids(self.domain), [])
        self.assertEqual(self.user.get_location_id(self.domain), None)

    def test_update_locations_succeeds(self):
        self.commcare_user_updater.update('location',
               {'primary_location': self.loc1.location_id,
                'locations': [self.loc1.location_id, self.loc2.location_id]})
        self.assertEqual(self.user.get_location_ids(self.domain), [self.loc1.location_id, self.loc2.location_id])
        self.assertEqual(self.user.get_location_id(self.domain), self.loc1.location_id)


class TestUpdateUserMethodsLogChanges(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.domain = 'test-domain'
        cls.domain_obj = create_domain(cls.domain)
        cls.addClassCleanup(cls.domain_obj.delete)
        cls.loc_type = LocationType.objects.create(domain=cls.domain, name='loc_type')
        cls.loc1 = SQLLocation.objects.create(
            location_id='loc1', location_type=cls.loc_type, domain=cls.domain)
        cls.loc2 = SQLLocation.objects.create(
            location_id='loc2', location_type=cls.loc_type, domain=cls.domain)

    def setUp(self) -> None:
        super().setUp()
        self.user = CommCareUser.create('test-domain', 'test-username', 'qwer1234', None, None)
        self.addCleanup(self.user.delete, self.domain, deleted_by=None)

        self.user_change_logger = UserChangeLogger(
            upload_domain=self.domain,
            user_domain=self.domain,
            user=self.user,
            is_new_user=False,
            changed_by_user=self.user,
            changed_via=USER_CHANGE_VIA_API,
            upload_record_id=None,
            user_domain_required_for_log=True
        )
        self.commcare_user_updater = CommcareUserUpdates(self.user, self.domain, self.user_change_logger)

    def test_update_password_logs_change(self):
        self.commcare_user_updater.update('password', 'a7d8fhjkdf8d')
        self.assertIn(PASSWORD_FIELD, self.user_change_logger.change_messages.keys())

    def test_update_email_logs_change(self):
        self.user.email = 'initial@dimagi.com'
        self.commcare_user_updater.update('email', 'updated@dimagi.com')
        self.assertIn('email', self.user_change_logger.fields_changed.keys())

    def test_update_email_with_no_change_does_not_log_change(self):
        self.user.email = 'unchanged@dimagi.com'
        self.commcare_user_updater.update('email', 'unchanged@dimagi.com')
        self.assertNotIn('email', self.user_change_logger.fields_changed.keys())

    def test_update_first_name_logs_change(self):
        self.user.first_name = 'Initial'
        self.user.save()
        self.commcare_user_updater.update('first_name', 'Updated')
        self.assertIn('first_name', self.user_change_logger.fields_changed.keys())

    def test_update_first_name_does_not_log_no_change(self):
        self.user.first_name = 'Unchanged'
        self.commcare_user_updater.update('first_name', 'Unchanged')
        self.assertNotIn('first_name', self.user_change_logger.fields_changed.keys())

    def test_update_last_name_logs_change(self):
        self.user.last_name = 'Initial'
        self.commcare_user_updater.update('last_name', 'Updated')
        self.assertIn('last_name', self.user_change_logger.fields_changed.keys())

    def test_update_last_name_does_not_log_no_change(self):
        self.user.last_name = 'Unchanged'
        self.commcare_user_updater.update('last_name', 'Unchanged')
        self.assertNotIn('last_name', self.user_change_logger.fields_changed.keys())

    def test_update_language_logs_change(self):
        self.user.language = 'in'
        self.commcare_user_updater.update('language', 'up')
        self.assertIn('language', self.user_change_logger.fields_changed.keys())

    def test_update_language_does_not_log_no_change(self):
        self.user.language = 'un'
        self.commcare_user_updater.update('language', 'un')
        self.assertNotIn('language', self.user_change_logger.fields_changed.keys())

    def test_update_default_phone_number_logs_change(self):
        self.user.set_default_phone_number('50253311398')
        self.commcare_user_updater.update('default_phone_number', '50253311399')
        self.assertIn('phone_numbers', self.user_change_logger.change_messages.keys())

    def test_update_default_phone_number_does_not_log_no_change(self):
        self.user.set_default_phone_number('50253311399')
        self.commcare_user_updater.update('default_phone_number', '50253311399')
        self.assertNotIn('phone_numbers', self.user_change_logger.change_messages.keys())

    def test_update_phone_numbers_logs_changes(self):
        self.user.phone_numbers = ['50253311398']
        self.commcare_user_updater.update('phone_numbers', ['50253311399'])
        self.assertIn('phone_numbers', self.user_change_logger.change_messages.keys())

    def test_update_phone_numbers_does_not_log_no_change(self):
        self.user.phone_numbers = ['50253311399', '50253311398']

        self.commcare_user_updater.update('phone_numbers', ['50253311399', '50253311398'])

        self.assertNotIn('phone_numbers', self.user_change_logger.change_messages.keys())

    def test_update_user_data_logs_change(self):
        self.user.get_user_data(self.domain)['custom_data'] = "initial custom data"

        self.commcare_user_updater.update('user_data', {'custom_data': 'updated custom data'})

        self.assertIn('user_data', self.user_change_logger.fields_changed.keys())

    def test_update_user_data_does_not_log_no_change(self):
        self.user.get_user_data(self.domain)['custom_data'] = "unchanged custom data"
        self.commcare_user_updater.update('user_data', {'custom_data': 'unchanged custom data'})
        self.assertNotIn('user_data', self.user_change_logger.fields_changed.keys())

    def test_update_groups_logs_change(self):
        group = Group({"name": "test", "domain": self.user.domain})
        group.save()
        self.addCleanup(group.delete)
        self.commcare_user_updater.update('groups', [group._id])
        self.assertIn(GROUPS_FIELD, self.user_change_logger.change_messages.keys())

    def test_update_groups_does_not_log_no_change(self):
        group = Group({"name": "test", "domain": self.user.domain})
        group.save()
        self.user.set_groups([group._id])
        self.addCleanup(group.delete)
        self.commcare_user_updater.update('groups', [group._id])
        self.assertNotIn(GROUPS_FIELD, self.user_change_logger.change_messages.keys())

    def test_update_user_role_logs_change(self):
        UserRole.create(
            self.domain, 'edit-data', permissions=HqPermissions(edit_data=True)
        )
        self.commcare_user_updater.update('role', 'edit-data')
        self.assertIn(ROLE_FIELD, self.user_change_logger.change_messages.keys())

    def test_update_user_role_does_not_logs_change(self):
        role = UserRole.create(
            self.domain, 'edit-data', permissions=HqPermissions(edit_data=True)
        )
        self.user.set_role(self.domain, role.get_qualified_id())

        self.commcare_user_updater.update('role', 'edit-data')

        self.assertNotIn(ROLE_FIELD, self.user_change_logger.change_messages.keys())

    def test_update_location_logs_change(self):
        self.commcare_user_updater.update('location',
                             {'primary_location': self.loc1.location_id,
                              'locations': [self.loc1.location_id, self.loc2.location_id]})
        self.assertIn(LOCATION_FIELD, self.user_change_logger.change_messages.keys())

    def test_update_location_without_include_location_fields_does_not_log_change(self):
        self.commcare_user_updater.update('location',
                             {'primary_location': None, 'locations': None})
        self.assertNotIn(LOCATION_FIELD, self.user_change_logger.change_messages.keys())

    def test_update_location_with_current_locations_does_not_log_change(self):
        self.user.set_location(self.loc2)
        self.user.set_location(self.loc1)
        self.commcare_user_updater.update('location',
                {'primary_location': self.loc1.location_id,
                'locations': [self.loc1.location_id, self.loc2.location_id]})
        self.assertNotIn(LOCATION_FIELD, self.user_change_logger.change_messages.keys())
