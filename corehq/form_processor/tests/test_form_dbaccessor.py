import uuid

from datetime import datetime
from django.core.files.uploadedfile import UploadedFile
from django.test import TestCase

from casexml.apps.case.mock import CaseBlock
from corehq.form_processor.backends.sql.dbaccessors import FormAccessorSQL, CaseAccessorSQL
from corehq.form_processor.backends.sql.processor import FormProcessorSQL
from corehq.form_processor.exceptions import XFormNotFound, AttachmentNotFound
from corehq.form_processor.models import XFormInstanceSQL, XFormOperationSQL, Attachment, CommCareCaseSQL, \
    CaseTransaction
from crispy_forms.tests.utils import override_settings

DOMAIN = 'test-form-accessor'

SIMPLE_FORM = """<?xml version='1.0' ?>
<data uiVersion="1" version="17" name="New Form" xmlns:jrm="http://dev.commcarehq.org/jr/xforms"
    xmlns="http://openrosa.org/formdesigner/form-processor">
    <dalmation_count>yes</dalmation_count>
    <n1:meta xmlns:n1="http://openrosa.org/jr/xforms">
        <n1:deviceID>DEV IL</n1:deviceID>
        <n1:timeStart>2013-04-19T16:52:41.000-04</n1:timeStart>
        <n1:timeEnd>2013-04-19T16:53:02.799-04</n1:timeEnd>
        <n1:username>eve</n1:username>
        <n1:userID>cruella_deville</n1:userID>
        <n1:instanceID>{uuid}</n1:instanceID>
        <n2:appVersion xmlns:n2="http://commcarehq.org/xforms"></n2:appVersion>
    </n1:meta>
    {case_block}
</data>"""


@override_settings(TESTS_SHOULD_USE_SQL_BACKEND=True)
class FormAccessorTests(TestCase):
    dependent_apps = []

    def test_get_form_by_id(self):
        form_id = _create_form()
        with self.assertNumQueries(1):
            form = FormAccessorSQL.get_form(form_id)
        self._check_simple_form(form)

    def test_get_form_by_id_missing(self):
        with self.assertRaises(XFormNotFound):
            FormAccessorSQL.get_form('missing_form')

    def test_get_forms(self):
        form_id1 = _create_form()
        form_id2 = _create_form()

        forms = FormAccessorSQL.get_forms(['missing_form'])
        self.assertEqual([], forms)

        forms = FormAccessorSQL.get_forms([form_id1])
        self.assertEqual(1, len(forms))
        self.assertEqual(form_id1, forms[0].form_id)

        forms = FormAccessorSQL.get_forms([form_id1, form_id2], ordered=True)
        self.assertEqual(2, len(forms))
        self.assertEqual(form_id1, forms[0].form_id)
        self.assertEqual(form_id2, forms[1].form_id)

    def test_get_with_attachments(self):
        form_id = _create_form()
        form = FormAccessorSQL.get_form(form_id)
        with self.assertNumQueries(1):
            form.get_attachment_meta('form.xml')

        with self.assertNumQueries(2):
            form = FormAccessorSQL.get_with_attachments(form_id)

        self._check_simple_form(form)
        with self.assertNumQueries(0):
            attachment_meta = form.get_attachment_meta('form.xml')

        self.assertEqual(form_id, attachment_meta.form_id)
        self.assertEqual('form.xml', attachment_meta.name)
        self.assertEqual('text/xml', attachment_meta.content_type)

    def test_get_attachment_by_name(self):
        form_id = _create_form()
        form_xml = _get_form_data(form_id)

        with self.assertRaises(AttachmentNotFound):
            FormAccessorSQL.get_attachment_by_name(form_id, 'not_a_form.xml')

        with self.assertNumQueries(1):
            attachment_meta = FormAccessorSQL.get_attachment_by_name(form_id, 'form.xml')

        self.assertEqual(form_id, attachment_meta.form_id)
        self.assertEqual('form.xml', attachment_meta.name)
        self.assertEqual('text/xml', attachment_meta.content_type)
        self.assertEqual(form_xml, attachment_meta.read_content())

    def test_get_form_operations(self):
        form_id = _create_form()

        operations = FormAccessorSQL.get_form_operations('missing_form')
        self.assertEqual([], operations)

        operations = FormAccessorSQL.get_form_operations(form_id)
        self.assertEqual([], operations)

        # don't call form.archive to avoid sending the signals
        FormAccessorSQL.archive_form(form_id, user_id='user1')
        FormAccessorSQL.unarchive_form(form_id, user_id='user2')

        operations = FormAccessorSQL.get_form_operations(form_id)
        self.assertEqual(2, len(operations))
        self.assertEqual('user1', operations[0].user_id)
        self.assertEqual(XFormOperationSQL.ARCHIVE, operations[0].operation)
        self.assertIsNotNone(operations[0].date)
        self.assertEqual('user2', operations[1].user_id)
        self.assertEqual(XFormOperationSQL.UNARCHIVE, operations[1].operation)
        self.assertIsNotNone(operations[1].date)
        self.assertGreater(operations[1].date, operations[0].date)

    def test_get_forms_with_attachments_meta(self):
        attachment_file = open('./corehq/ex-submodules/casexml/apps/case/tests/data/attachments/fruity.jpg', 'rb')
        attachments = {
            'pic.jpg': UploadedFile(attachment_file, 'pic.jpg', content_type='image/jpeg')
        }
        form_with_pic_id = _create_form(attachments=attachments)
        plain_form_id = _create_form()

        forms = FormAccessorSQL.get_forms_with_attachments_meta([form_with_pic_id, plain_form_id])
        self.assertEqual(2, len(forms))
        self.assertEqual(form_with_pic_id, forms[0].form_id)
        with self.assertNumQueries(0):
            expected = {
                'form.xml': 'text/xml',
                'pic.jpg': 'image/jpeg',
            }
            attachments = forms[0].get_attachments()
            self.assertEqual(2, len(attachments))
            self.assertEqual(expected, {att.name: att.content_type for att in attachments})

        with self.assertNumQueries(0):
            expected = {
                'form.xml': 'text/xml',
            }
            attachments = forms[1].get_attachments()
            self.assertEqual(1, len(attachments))
            self.assertEqual(expected, {att.name: att.content_type for att in attachments})

    def test_get_forms_by_type(self):
        form_id1 = _create_form()
        form_id2 = _create_form()

        # basic check
        forms = FormAccessorSQL.get_forms_by_type(DOMAIN, 'XFormInstance', 5)
        self.assertEqual(2, len(forms))
        self.assertEqual([form_id1, form_id2], [f.form_id for f in forms])

        # check reverse ordering
        forms = FormAccessorSQL.get_forms_by_type(DOMAIN, 'XFormInstance', 5, recent_first=True)
        self.assertEqual(2, len(forms))
        self.assertEqual([form_id2, form_id1], [f.form_id for f in forms])

        # check limit
        forms = FormAccessorSQL.get_forms_by_type(DOMAIN, 'XFormInstance', 1)
        self.assertEqual(1, len(forms))
        self.assertEqual(form_id1, forms[0].form_id)

        # change state of form1
        FormAccessorSQL.archive_form(form_id1, 'user1')

        # check filtering by state
        forms = FormAccessorSQL.get_forms_by_type(DOMAIN, 'XFormArchived', 2)
        self.assertEqual(1, len(forms))
        self.assertEqual(form_id1, forms[0].form_id)

        forms = FormAccessorSQL.get_forms_by_type(DOMAIN, 'XFormInstance', 2)
        self.assertEqual(1, len(forms))
        self.assertEqual(form_id2, forms[0].form_id)

    def test_form_with_id_exists(self):
        form_id1 = _create_form()

        self.assertFalse(FormAccessorSQL.form_with_id_exists('not a form'))
        self.assertFalse(FormAccessorSQL.form_with_id_exists(form_id1, 'wrong domain'))
        self.assertTrue(FormAccessorSQL.form_with_id_exists(form_id1))
        self.assertTrue(FormAccessorSQL.form_with_id_exists(form_id1, DOMAIN))

    def test_hard_delete_forms(self):
        form_ids = [_create_form() for i in range(3)]
        other_form_id = _create_form(domain='other_domain')
        self.addCleanup(lambda: FormAccessorSQL.hard_delete_forms('other_domain', [other_form_id]))
        forms = FormAccessorSQL.get_forms(form_ids)
        self.assertEqual(3, len(forms))

        deleted = FormAccessorSQL.hard_delete_forms(DOMAIN, form_ids[1:] + [other_form_id])
        self.assertEqual(2, deleted)
        forms = FormAccessorSQL.get_forms(form_ids)
        self.assertEqual(1, len(forms))
        self.assertEqual(form_ids[0], forms[0].form_id)

    def test_archive_unarchive_form(self):
        case_id = uuid.uuid4().hex
        form_id = _create_form(case_id=case_id)
        form = FormAccessorSQL.get_form(form_id)
        self.assertEqual(XFormInstanceSQL.NORMAL, form.state)
        self.assertEqual(0, len(form.history))

        transactions = CaseAccessorSQL.get_transactions(case_id)
        self.assertEqual(1, len(transactions))
        self.assertFalse(transactions[0].revoked)

        FormAccessorSQL.archive_form(form_id, 'user1')
        form = FormAccessorSQL.get_form(form_id)
        self.assertEqual(XFormInstanceSQL.ARCHIVED, form.state)
        operations = form.history
        self.assertEqual(1, len(operations))
        self.assertEqual(form_id, operations[0].form_id)
        self.assertEqual('user1', operations[0].user_id)

        transactions = CaseAccessorSQL.get_transactions(case_id)
        self.assertEqual(1, len(transactions))
        self.assertTrue(transactions[0].revoked)

        FormAccessorSQL.unarchive_form(form_id, 'user2')
        form = FormAccessorSQL.get_form(form_id)
        self.assertEqual(XFormInstanceSQL.NORMAL, form.state)
        operations = form.history
        self.assertEqual(2, len(operations))
        self.assertEqual(form_id, operations[1].form_id)
        self.assertEqual('user2', operations[1].user_id)

        transactions = CaseAccessorSQL.get_transactions(case_id)
        self.assertEqual(1, len(transactions))
        self.assertFalse(transactions[0].revoked)

    def _check_simple_form(self, form):
        self.assertIsInstance(form, XFormInstanceSQL)
        self.assertIsNotNone(form)
        self.assertEqual(DOMAIN, form.domain)
        self.assertEqual('user1', form.user_id)
        return form


def _create_form(domain=None, case_id=None, attachments=None):
    """
    Create the models directly so that these tests aren't dependent on any
    other apps. Not testing form processing here anyway.
    :param case_id: create case with ID if supplied
    :param attachments: additional attachments dict
    :return: form_id
    """
    domain = domain or DOMAIN
    form_id = uuid.uuid4().hex
    user_id = 'user1'
    utcnow = datetime.utcnow()

    form_data = _get_form_data(form_id, case_id)

    form = XFormInstanceSQL(
        form_id=form_id,
        xmlns='http://openrosa.org/formdesigner/form-processor',
        received_on=utcnow,
        user_id=user_id,
        domain=domain
    )

    attachments = attachments or {}
    attachment_tuples = map(
        lambda a: Attachment(name=a[0], raw_content=a[1], content_type=a[1].content_type),
        attachments.items()
    )
    attachment_tuples.append(Attachment('form.xml', form_data, 'text/xml'))

    FormProcessorSQL.store_attachments(form, attachment_tuples)

    cases = []
    if case_id:
        case = CommCareCaseSQL(
            case_id=case_id,
            domain=DOMAIN,
            type='',
            owner_id=user_id,
            opened_on=utcnow,
            modified_on=utcnow,
            modified_by=user_id,
            server_modified_on=utcnow,
        )
        case.track_create(CaseTransaction.form_transaction(case, form))
        cases = [case]

    FormProcessorSQL.save_processed_models([form], cases)
    return form_id


def _get_form_data(form_id, case_id=None):
    case_block = ''
    if case_id:
        case_block = CaseBlock(create=True, case_id=case_id).as_string()
    form_data = SIMPLE_FORM.format(uuid=form_id, case_block=case_block)
    return form_data
