import uuid
from decimal import Decimal

from django.test import TestCase

from couchdbkit import ResourceNotFound

from corehq.apps.toggle_ui.models import ToggleAudit
from corehq.toggles import NAMESPACE_USER, NAMESPACE_DOMAIN
from toggle.models import Toggle

from corehq.apps.toggle_ui.migration_helpers import move_toggles


class MigrationHelperTest(TestCase):

    @staticmethod
    def _delete_toggles(self, *toggles):
        for toggle in toggles:
            try:
                Toggle.get(toggle).delete()
            except ResourceNotFound:
                pass

    def test_move_nonexistent_source(self):
        dsa = uuid.uuid4().hex
        try:
            Toggle(slug=dsa, enabled_users=['kieran']).save()
            move_toggles('missing-src', dsa)
            self.assertEqual(['kieran'], Toggle.get(dsa).enabled_users)
        finally:
            MigrationHelperTest._delete_toggles(dsa)

    def test_move_nonexistent_destination(self):
        moz, dsa = [uuid.uuid4().hex for i in range(2)]
        try:
            Toggle(slug=moz, enabled_users=['claire']).save()
            move_toggles(moz, dsa)
            dsa_toggle = Toggle.get(dsa)
            self.assertEqual(['claire'], dsa_toggle.enabled_users)
            with self.assertRaises(ResourceNotFound):
                Toggle.get(moz)
        finally:
            MigrationHelperTest._delete_toggles(moz, dsa)

    def test_move(self):
        moz, dsa = [uuid.uuid4().hex for i in range(2)]
        try:
            moz_users = ['marco', 'lauren', 'claire']
            dsa_users = ['kieran', 'jolani', 'claire']
            Toggle(slug=moz, enabled_users=moz_users).save()
            Toggle(slug=dsa, enabled_users=dsa_users).save()
            move_toggles(moz, dsa)
            # ensure original is delted
            with self.assertRaises(ResourceNotFound):
                Toggle.get(moz)
            dsa_toggle = Toggle.get(dsa)
            expected_users = set(moz_users) | set(dsa_users)
            self.assertEqual(len(expected_users), len(dsa_toggle.enabled_users))
            self.assertEqual(expected_users, set(dsa_toggle.enabled_users))
        finally:
            MigrationHelperTest._delete_toggles(moz, dsa)


class TestToggleAudit(TestCase):
    def test_log_toggle_changes(self):
        slug = uuid.uuid4().hex
        ToggleAudit.objects.log_toggle_changes(
            slug, "username1", {"domain:item1", "item2"}, {"item2", "item3"}, 0.001
        )
        query = ToggleAudit.objects.filter(slug=slug)
        self.assertEqual(3, query.count())
        add = query.filter(action=ToggleAudit.ACTION_ADD).all()
        self.assertEqual(1, len(add))
        self.assertEqual(add[0].username, "username1")
        self.assertEqual(add[0].item, "item1")
        self.assertEqual(add[0].namespace, NAMESPACE_DOMAIN)

        remove = query.filter(action=ToggleAudit.ACTION_REMOVE).all()
        self.assertEqual(1, len(remove))
        self.assertEqual(remove[0].username, "username1")
        self.assertEqual(remove[0].item, "item3")
        self.assertEqual(remove[0].namespace, NAMESPACE_USER)

        randomness = query.filter(action=ToggleAudit.ACTION_UPDATE_RANDOMNESS).all()
        self.assertEqual(1, len(randomness))
        self.assertEqual(randomness[0].username, "username1")
        self.assertAlmostEqual(randomness[0].randomness, Decimal(0.001))
