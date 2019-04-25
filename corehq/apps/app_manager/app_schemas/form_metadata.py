from __future__ import absolute_import, unicode_literals

from collections import defaultdict

import six

from corehq.apps.app_manager.app_schemas.app_case_metadata import (
    AppCaseMetadata,
    LoadSaveProperty,
    FormQuestionResponse,
)
from corehq.apps.app_manager.exceptions import XFormException

from jsonobject import (
    BooleanProperty,
    DictProperty,
    JsonObject,
    ListProperty,
    ObjectProperty,
    StringProperty,
)

REMOVED = 'removed'
ADDED = 'added'
CHANGED = 'changed'

DIFF_STATES = (REMOVED, ADDED, CHANGED)

QUESTION_ATTRIBUTES = (
    'label', 'type', 'value', 'options', 'calculate', 'relevant',
    'required', 'comment', 'setvalue', 'constraint',
    'load_properties', 'save_properties'
)

FORM_ATTRIBUTES = (
    'name', 'short_comment', 'form_filter'
)

MODULE_ATTRIBUTES = (
    'name', 'short_comment', 'module_filter'
)


class _QuestionDiff(JsonObject):
    question = StringProperty(choices=(ADDED, REMOVED))
    label = StringProperty(choices=DIFF_STATES)
    type = StringProperty(choices=DIFF_STATES)
    value = StringProperty(choices=DIFF_STATES)
    calculate = StringProperty(choices=DIFF_STATES)
    relevant = StringProperty(choices=DIFF_STATES)
    required = StringProperty(choices=DIFF_STATES)
    comment = StringProperty(choices=DIFF_STATES)
    setvalue = StringProperty(choices=DIFF_STATES)
    constraint = StringProperty(choices=DIFF_STATES)
    options = DictProperty()    # {option: state}
    load_properties = DictProperty()  # {case_type: {property: state}}
    save_properties = DictProperty()  # {case_type: {property: state}}


class _FormDiff(JsonObject):
    form = StringProperty(choices=(ADDED, REMOVED))
    name = StringProperty(choices=DIFF_STATES)
    short_comment = StringProperty(choices=DIFF_STATES)
    form_filter = StringProperty(choices=DIFF_STATES)
    contains_changes = BooleanProperty(default=False)


class _ModuleDiff(JsonObject):
    module = StringProperty(choices=(ADDED, REMOVED))
    name = StringProperty(choices=DIFF_STATES)
    short_comment = StringProperty(choices=DIFF_STATES)
    module_filter = StringProperty(choices=DIFF_STATES)
    contains_changes = BooleanProperty(default=False)


class _FormMetadataQuestion(FormQuestionResponse):
    form_id = StringProperty()
    load_properties = ListProperty(LoadSaveProperty)
    save_properties = ListProperty(LoadSaveProperty)
    changes = ObjectProperty(_QuestionDiff)


class _FormMetadata(JsonObject):
    module_id = StringProperty()
    unique_id = StringProperty()
    name = DictProperty()
    short_comment = StringProperty()
    action_type = StringProperty()
    form_filter = StringProperty()
    questions = ListProperty(_FormMetadataQuestion)
    error = DictProperty()
    changes = ObjectProperty(_FormDiff)


class _ModuleMetadata(JsonObject):
    unique_id = StringProperty()
    name = DictProperty()
    short_comment = StringProperty()
    module_type = StringProperty()
    is_surveys = BooleanProperty()
    module_filter = StringProperty()
    forms = ListProperty(_FormMetadata)
    changes = ObjectProperty(_ModuleDiff)


class _AppSummaryFormDataGenerator(object):
    def __init__(self, domain, app, include_shadow_forms=True):
        self.domain = domain
        self.app = app
        self.include_shadow_forms = include_shadow_forms

        self.errors = []

        self._seen_save_to_case = defaultdict(list)
        try:
            self._case_meta = self.app.get_case_metadata()
        except XFormException:
            self._case_meta = AppCaseMetadata()

    def generate(self):
        return [self._compile_module(module) for module in self.app.get_modules()], self.errors

    def _compile_module(self, module):
        return _ModuleMetadata(**{
            'unique_id': module.unique_id,
            'name': module.name,
            'short_comment': module.short_comment,
            'module_type': module.module_type,
            'is_surveys': module.is_surveys,
            'module_filter': module.module_filter,
            'forms': [self._compile_form(form) for form in self._get_pertinent_forms(module)],
        })

    def _get_pertinent_forms(self, module):
        from corehq.apps.app_manager.models import ShadowForm
        if not self.include_shadow_forms:
            return [form for form in module.get_forms() if not isinstance(form, ShadowForm)]
        return module.get_forms()

    def _compile_form(self, module_id, form):
        form_meta = _FormMetadata(**{
            'module_id': module_id,
            'unique_id': form.unique_id,
            'name': form.name,
            'short_comment': form.short_comment,
            'action_type': form.get_action_type(),
            'form_filter': form.form_filter,
        })
        try:
            form_meta.questions = [
                question
                for raw_question in form.get_questions(self.app.langs, include_triggers=True,
                                                       include_groups=True, include_translations=True)
                for question in self._get_question(form.unique_id, raw_question)
            ]
        except XFormException as exception:
            form_meta.error = {
                'details': six.text_type(exception),
            }
            self.errors.append(form_meta)
        return form_meta

    def _get_question(self, form_unique_id, question):
        if self._needs_save_to_case_root_node(question, form_unique_id):
            yield self._save_to_case_root_node(form_unique_id, question)
        yield self._serialized_question(form_unique_id, question)

    def _needs_save_to_case_root_node(self, question, form_unique_id):
        return (
            self._is_save_to_case(question)
            and self._save_to_case_root_path(question) not in self._seen_save_to_case[form_unique_id]
        )

    @staticmethod
    def _is_save_to_case(question):
        return '/case/' in question['value']

    @staticmethod
    def _save_to_case_root_path(question):
        return question['value'].split('/case/')[0]

    def _save_to_case_root_node(self, form_unique_id, question):
        """Add an extra node with the root path of the save to case to attach case properties to
        """
        question_path = self._save_to_case_root_path(question)
        response = _FormMetadataQuestion(**{
            "form_id": form_unique_id,
            "label": question_path,
            "tag": question_path,
            "value": question_path,
            "repeat": question['repeat'],
            "group": question['group'],
            "type": 'SaveToCase',
            "hashtagValue": question['hashtagValue'],
            "relevant": None,
            "required": False,
            "comment": None,
            "constraint": None,
            "load_properties": self._case_meta.get_load_properties(form_unique_id, question_path),
            "save_properties": self._case_meta.get_save_properties(form_unique_id, question_path)
        })
        self._seen_save_to_case[form_unique_id].append(question_path)
        return response

    def _serialized_question(self, form_unique_id, question):
        response = _FormMetadataQuestion(question)
        response.form_id = form_unique_id
        response.load_properties = self._case_meta.get_load_properties(form_unique_id, question['value'])
        response.save_properties = self._case_meta.get_save_properties(form_unique_id, question['value'])
        if self._is_save_to_case(question):
            response.type = 'SaveToCase'
        return response


def get_app_summary_formdata(domain, app, include_shadow_forms=True):
    """Returns formdata formatted for the app summary
    """
    return _AppSummaryFormDataGenerator(domain, app, include_shadow_forms).generate()


class _AppDiffGenerator(object):
    def __init__(self, app1, app2):
        self.first = get_app_summary_formdata(app1.domain, app1)[0]
        self.second = get_app_summary_formdata(app2.domain, app2)[0]

        self._first_by_id = {}
        self._first_questions_by_form_id = defaultdict(dict)
        self._second_by_id = {}
        self._second_questions_by_form_id = defaultdict(dict)
        self._populate_id_caches()

        self._mark_removed_items()
        self._mark_retained_items()

    def _populate_id_caches(self):
        for module in self.first:
            self._first_by_id[module['unique_id']] = module
            for form in module['forms']:
                self._first_by_id[form['unique_id']] = form
                for question in form['questions']:
                    self._first_questions_by_form_id[form['unique_id']][question['value']] = question

        for module in self.second:
            self._second_by_id[module['unique_id']] = module
            for form in module['forms']:
                self._second_by_id[form['unique_id']] = form
                for question in form['questions']:
                    self._second_questions_by_form_id[form['unique_id']][question['value']] = question

    def _mark_removed_items(self):
        """Finds all removed modules, forms, and questions from the second app
        """
        for module in self.first:
            if module['unique_id'] not in self._second_by_id:
                self._mark_item_removed(module, 'module')
                continue

            for form in module['forms']:
                if form['unique_id'] not in self._second_by_id:
                    self._mark_item_removed(form, 'form')
                    continue

                for question in form['questions']:
                    if question.value not in self._second_questions_by_form_id[form['unique_id']]:
                        self._mark_item_removed(question, 'question')

    def _mark_retained_items(self):
        """Looks through each module and form that was not removed in the second app
        and marks changes and additions

        """
        for second_module in self.second:
            try:
                first_module = self._first_by_id[second_module['unique_id']]
                for attribute in MODULE_ATTRIBUTES:
                    self._mark_attribute(first_module, second_module, attribute)
                self._mark_forms(second_module['forms'])
            except KeyError:
                self._mark_item_added(second_module, 'module')

    def _mark_attribute(self, first_item, second_item, attribute):
        is_translatable_property = (isinstance(first_item[attribute], dict)
                                    and isinstance(second_item[attribute], dict))
        translation_changed = (is_translatable_property
                               and set(second_item[attribute].items()) - set(first_item[attribute].items()))
        attribute_changed = first_item[attribute] != second_item[attribute]
        attribute_added = second_item[attribute] and not first_item[attribute]
        attribute_removed = first_item[attribute] and not second_item[attribute]
        if attribute_changed or translation_changed:
            self._mark_item_changed(first_item, attribute)
            self._mark_item_changed(second_item, attribute)
        if attribute_added:
            self._mark_item_added(second_item, attribute)
        if attribute_removed:
            self._mark_item_removed(first_item, attribute)

    def _mark_forms(self, second_forms):
        for second_form in second_forms:
            try:
                first_form = self._first_by_id[second_form['unique_id']]
                for attribute in FORM_ATTRIBUTES:
                    self._mark_attribute(first_form, second_form, attribute)
                self._mark_questions(second_form['unique_id'], second_form['questions'])
            except KeyError:
                self._mark_item_added(second_form, 'form')

    def _mark_questions(self, form_id, second_questions):
        for second_question in second_questions:
            try:
                question_path = second_question['value']
                first_question = self._first_questions_by_form_id[form_id][question_path]
                self._mark_question_attributes(first_question, second_question)
            except KeyError:
                self._mark_item_added(second_question, 'question')

    def _mark_question_attributes(self, first_question, second_question):
        for attribute in QUESTION_ATTRIBUTES:
            if attribute == 'options':
                self._mark_options(first_question, second_question)
            elif attribute in ('save_properties', 'load_properties'):
                self._mark_case_properties(first_question, second_question, attribute)
            else:
                self._mark_attribute(first_question, second_question, attribute)

    def _mark_options(self, first_question, second_question):
        first_option_values = {option.value for option in first_question.options}
        second_option_values = {option.value for option in second_question.options}

        removed_options = first_option_values - second_option_values
        added_options = second_option_values - first_option_values

        potentially_changed_options = first_option_values & second_option_values
        first_options_by_value = {option.value: option.label for option in first_question.options}
        second_options_by_value = {option.value: option.label for option in second_question.options}
        changed_options = [
            option for option in potentially_changed_options
            if first_options_by_value[option] != second_options_by_value[option]
        ]

        for removed_option in removed_options:
            first_question.changes['options'][removed_option] = REMOVED

        for added_option in added_options:
            second_question.changes['options'][added_option] = ADDED

        for changed_option in changed_options:
            first_question.changes['options'][changed_option] = CHANGED
            second_question.changes['options'][changed_option] = CHANGED

        if removed_options or added_options or changed_options:
            self._set_contains_changes(first_question)
            self._set_contains_changes(second_question)

    def _mark_case_properties(self, first_question, second_question, attribute):
        first_props = {(prop.case_type, prop.property) for prop in first_question[attribute]}
        second_props = {(prop.case_type, prop.property) for prop in second_question[attribute]}
        removed_properties = first_props - second_props
        added_properties = second_props - first_props

        for removed_property in removed_properties:
            first_question.changes[attribute][removed_property[0]] = {removed_property[1]: REMOVED}
        for added_property in added_properties:
            second_question.changes[attribute][added_property[0]] = {added_property[1]: ADDED}

        if removed_properties or added_properties:
            self._set_contains_changes(first_question)
            self._set_contains_changes(second_question)

    def _mark_item_removed(self, item, key):
        self._set_contains_changes(item)
        item.changes[key] = REMOVED

    def _mark_item_added(self, item, key):
        self._set_contains_changes(item)
        item.changes[key] = ADDED

    def _mark_item_changed(self, item, key):
        self._set_contains_changes(item)
        item.changes[key] = CHANGED

    def _set_contains_changes(self, item):
        """For forms and modules, set contains_changes to True
        For questions, set the form's contains_changes attribute to True

        This is used for the "View Changed Items" filter in the UI
        """
        try:
            for form in self._get_form_ancestors(item):
                form.changes.contains_changes = True
            item.changes.contains_changes = True
        except AttributeError:
            pass

    def _get_form_ancestors(self, question):
        """Returns forms from both apps with the same form_id.
        If something other than a question is passed in, it will be ignored

        """
        ancestors = []
        for tree in [self._first_by_id, self._second_by_id]:
            try:
                form_id = question['form_id']
                ancestors.append(tree[form_id])
            except KeyError:
                continue
        return ancestors


def get_app_diff(app1, app2):
    diff = _AppDiffGenerator(app1, app2)
    return diff.first, diff.second
