import attr
from couchdbkit import BadValueError
from jsonpath_rw import parse as parse_jsonpath

from couchforms.const import TAG_FORM, TAG_META
from dimagi.ext.couchdbkit import (
    DictProperty,
    DocumentSchema,
    Property,
    StringProperty,
)

from corehq.apps.locations.models import SQLLocation
from corehq.apps.users.cases import get_owner_id, get_wrapped_owner
from corehq.motech.const import (
    COMMCARE_DATA_TYPE_DECIMAL,
    COMMCARE_DATA_TYPE_INTEGER,
    COMMCARE_DATA_TYPE_TEXT,
    COMMCARE_DATA_TYPES,
    DATA_TYPE_UNKNOWN,
    DIRECTION_BOTH,
    DIRECTION_EXPORT,
    DIRECTION_IMPORT,
    DIRECTIONS,
)
from corehq.motech.serializers import serializers


@attr.s
class CaseTriggerInfo:
    domain = attr.ib()
    case_id = attr.ib()
    type = attr.ib(default=None)
    name = attr.ib(default=None)
    owner_id = attr.ib(default=None)
    modified_by = attr.ib(default=None)
    updates = attr.ib(factory=dict)
    created = attr.ib(default=None)
    closed = attr.ib(default=None)
    extra_fields = attr.ib(factory=dict)
    form_question_values = attr.ib(factory=dict)

    def __str__(self):
        if self.name:
            return f'<CaseTriggerInfo {self.case_id} {self.name!r}>'
        return f"<CaseTriggerInfo {self.case_id}>"


def not_blank(value):
    if not str(value):
        raise BadValueError("Value cannot be blank.")


def recurse_subclasses(cls):
    return (
        cls.__subclasses__() +
        [subsub for sub in cls.__subclasses__() for subsub in recurse_subclasses(sub)]
    )


class ValueSource(DocumentSchema):
    """
    Subclasses model a reference to a value, like a case property or a
    form question.

    Use the `get_value()` method to fetch the value using the reference,
    and serialize it, if necessary, for the external system that it is
    being sent to.
    """
    external_data_type = StringProperty(required=False, default=DATA_TYPE_UNKNOWN, exclude_if_none=True)
    commcare_data_type = StringProperty(required=False, default=DATA_TYPE_UNKNOWN, exclude_if_none=True,
                                        choices=COMMCARE_DATA_TYPES + (DATA_TYPE_UNKNOWN,))
    # Whether the ValueSource is import-only ("in"), export-only ("out"), or
    # for both import and export (the default, None)
    direction = StringProperty(required=False, default=DIRECTION_BOTH, exclude_if_none=True,
                               choices=DIRECTIONS)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (
            self.doc_type == other.doc_type
            and self.external_data_type == other.external_data_type
            and self.commcare_data_type == other.commcare_data_type
            and self.direction == other.direction
        )

    @classmethod
    def wrap(cls, data):
        if cls is ValueSource:
            subclass = {
                sub._doc_type: sub for sub in recurse_subclasses(cls)
            }.get(data['doc_type'])
            return subclass.wrap(data) if subclass else None
        else:
            return super(ValueSource, cls).wrap(data)

    @property
    def can_import(self):
        return not self.direction or self.direction == DIRECTION_IMPORT

    @property
    def can_export(self):
        return not self.direction or self.direction == DIRECTION_EXPORT


class CaseProperty(ValueSource):
    """
    A reference to a case property
    """
    # Example "person_property" value::
    #
    #     {
    #       "birthdate": {
    #         "doc_type": "CaseProperty",
    #         "case_property": "dob"
    #       }
    #     }
    #
    case_property = StringProperty(required=True, validators=not_blank)


class FormQuestion(ValueSource):
    """
    A reference to a form question
    """
    form_question = StringProperty()  # e.g. "/data/foo/bar"


class ConstantString(ValueSource):
    """
    A constant value.

    Use the model's data types for the `serialize()` method to convert
    the value for the external system, if necessary.
    """
    # Example "person_property" value::
    #
    #     {
    #       "birthdate": {
    #         "doc_type": "ConstantString",
    #         "value": "Sep 7, 3761 BC"
    #       }
    #     }
    #
    value = StringProperty()

    def __eq__(self, other):
        return (
            super(ConstantString, self).__eq__(other) and
            self.value == other.value
        )


class ConstantValue(ConstantString):
    """
    ConstantValue provides a ValueSource for constant values.

    ``value`` must be cast as ``value_data_type``.

    ``deserialize()`` returns the value for import. Use
    ``commcare_data_type`` to cast the import value.

    ``ConstantValue.get_value(case_trigger_info)`` returns the value for
    export.

    >>> one = ConstantValue.wrap({
    ...     "value": 1,
    ...     "value_data_type": COMMCARE_DATA_TYPE_INTEGER,
    ...     "commcare_data_type": COMMCARE_DATA_TYPE_DECIMAL,
    ...     "external_data_type": COMMCARE_DATA_TYPE_TEXT,
    ... })
    >>> info = CaseTriggerInfo("test-domain", None)
    >>> deserialize(one, "foo")
    1.0
    >>> get_value(one, info)  # Returns '1.0', not '1'. See note below.
    '1.0'

    .. NOTE::
       ``one.get_value(info)`` returns  ``'1.0'``, not ``'1'``, because
       ``get_commcare_value()`` casts ``value`` as
       ``commcare_data_type`` first. ``serialize()`` casts it from
       ``commcare_data_type`` to ``external_data_type``.

       This may seem counter-intuitive, but we do it to preserve the
       behaviour of ``serialize()`` because it is public and is used
       outside the class.

    """
    value = Property()
    value_data_type = StringProperty(default=COMMCARE_DATA_TYPE_TEXT)

    def __eq__(self, other):
        return (
            super().__eq__(other)
            and self.value_data_type == other.value_data_type
        )


class CasePropertyMap(CaseProperty):
    """
    Maps case property values to OpenMRS values or concept UUIDs
    """
    # Example "person_attribute" value::
    #
    #     {
    #       "00000000-771d-0000-0000-000000000000": {
    #         "doc_type": "CasePropertyMap",
    #         "case_property": "pill"
    #         "value_map": {
    #           "red": "00ff0000-771d-0000-0000-000000000000",
    #           "blue": "000000ff-771d-0000-0000-000000000000",
    #         }
    #       }
    #     }
    #
    value_map = DictProperty()


class FormQuestionMap(FormQuestion):
    """
    Maps form question values to OpenMRS values or concept UUIDs
    """
    value_map = DictProperty()


class CaseOwnerAncestorLocationField(ValueSource):
    """
    A reference to a location metadata value. The location may be the
    case owner, the case owner's location, or the first ancestor
    location of the case owner where the metadata value is set.
    """
    location_field = StringProperty()


class FormUserAncestorLocationField(ValueSource):
    """
    A reference to a location metadata value. The location is the form
    user's location, or the first ancestor location of the form user
    where the metadata value is set.
    """
    location_field = StringProperty()


class JsonPathMixin(DocumentSchema):
    """
    Used for importing a value from a JSON document.
    """
    jsonpath = StringProperty(required=True, validators=not_blank)


class JsonPathCaseProperty(CaseProperty, JsonPathMixin):
    pass


class JsonPathCasePropertyMap(CasePropertyMap, JsonPathMixin):
    pass


class CasePropertyConstantValue(ConstantValue, CaseProperty):
    pass


def get_value(value_source, case_trigger_info):
    """
    Returns the value referred to by the ValueSource, serialized for
    the external system.
    """
    value = get_commcare_value(value_source, case_trigger_info)
    return serialize(value_source, value)


def get_import_value(value_source, external_data):
    external_value = get_external_value(value_source, external_data)
    return deserialize(value_source, external_value)


def get_commcare_value(value_source, case_trigger_info):

    if hasattr(value_source, "value"):
        if hasattr(value_source, "value_data_type"):
            # ConstantValue
            serializer = (
                serializers.get((value_source.value_data_type, value_source.commcare_data_type))
                or serializers.get((None, value_source.commcare_data_type))
            )
            return serializer(value_source.value) if serializer else value_source.value
        else:
            # ConstantString
            return value_source.value

    if hasattr(value_source, "form_question"):
        # FormQuestion or FormQuestionMap
        return case_trigger_info.form_question_values.get(
            value_source.form_question
        )

    if hasattr(value_source, "case_property"):
        # CaseProperty or CasePropertyMap
        if value_source.case_property in case_trigger_info.updates:
            return case_trigger_info.updates[value_source.case_property]
        return case_trigger_info.extra_fields.get(value_source.case_property)

    if hasattr(value_source, "location_field"):
        # CaseOwnerAncestorLocationField or FormUserAncestorLocationField
        if value_source.doc_type == "CaseOwnerAncestorLocationField":
            location = get_case_location(case_trigger_info)
        elif value_source.doc_type == "FormUserAncestorLocationField":
            user_id = case_trigger_info.form_question_values.get('/metadata/userID')
            location = get_owner_location(case_trigger_info.domain, user_id)
        else:
            raise TypeError(f"Unrecognised value source {value_source!r}")
        if location:
            return get_ancestor_location_metadata_value(
                location, value_source.location_field
            )


def get_external_value(value_source, external_data):
    if (
        hasattr(value_source, "value")
        and hasattr(value_source, "value_data_type")
    ):
        serializer = (
            serializers.get((value_source.value_data_type, value_source.external_data_type))
            or serializers.get((None, value_source.external_data_type))
        )
        return serializer(value_source.value) if serializer else value_source.value
    if hasattr(value_source, "jsonpath"):
        jsonpath = parse_jsonpath(value_source.jsonpath)
        matches = jsonpath.find(external_data)
        values = [m.value for m in matches]
        if not values:
            return None
        elif len(values) == 1:
            return values[0]
        else:
            return values


def serialize(value_source, value):
    """
    Converts the value's CommCare data type or format to its data
    type or format for the external system, if necessary, otherwise
    returns the value unchanged.
    """
    if hasattr(value_source, "value_map"):
        return value_source.value_map.get(value)
    serializer = (
        serializers.get((value_source.commcare_data_type, value_source.external_data_type))
        or serializers.get((None, value_source.external_data_type))
    )
    return serializer(value) if serializer else value


def deserialize(value_source, external_value):
    """
    Converts the value's external data type or format to its data
    type or format for CommCare, if necessary, otherwise returns the
    value unchanged.
    """
    if hasattr(value_source, "value"):
        if hasattr(value_source, "value_data_type"):
            # ConstantValue
            serializer = (
                serializers.get((value_source.value_data_type, value_source.external_data_type))
                or serializers.get((None, value_source.external_data_type))
            )
            external_value = serializer(value_source.value) if serializer else value_source.value
        else:
            # ConstantString
            return None
    if hasattr(value_source, "value_map"):
        reverse_map = {v: k for k, v in value_source.value_map.items()}
        return reverse_map.get(external_value)
    serializer = (
        serializers.get((value_source.external_data_type, value_source.commcare_data_type))
        or serializers.get((None, value_source.commcare_data_type))
    )
    return serializer(external_value) if serializer else external_value


def get_form_question_values(form_json):
    """
    Given form JSON, returns question-value pairs, where questions are
    formatted "/data/foo/bar".

    e.g. Question "bar" in group "foo" has value "baz":

    >>> get_form_question_values({'form': {'foo': {'bar': 'baz'}}})
    {'/data/foo/bar': 'baz'}

    """
    _reserved_keys = ('@uiVersion', '@xmlns', '@name', '#type', 'case', 'meta', '@version')

    def _recurse_form_questions(form_dict, path, result_):
        for key, value in form_dict.items():
            if key in _reserved_keys:
                continue
            new_path = path + [key]
            if isinstance(value, list):
                # Repeat group
                for v in value:
                    assert isinstance(v, dict)
                    _recurse_form_questions(v, new_path, result_)
            elif isinstance(value, dict):
                # Group
                _recurse_form_questions(value, new_path, result_)
            else:
                # key is a question and value is its answer
                question = '/'.join((p.decode('utf8') if isinstance(p, bytes) else p for p in new_path))
                result_[question] = value

    result = {}
    _recurse_form_questions(form_json[TAG_FORM], [b'/data'], result)  # "/data" is just convention, hopefully
    # familiar from form builder. The form's data will usually be immediately under "form_json[TAG_FORM]" but not
    # necessarily. If this causes problems we may need a more reliable way to get to it.

    metadata = {}
    if 'meta' in form_json[TAG_FORM]:
        metadata.update(form_json[TAG_FORM][TAG_META])
    if 'received_on' in form_json:
        metadata['received_on'] = form_json['received_on']
    if metadata:
        _recurse_form_questions(metadata, [b'/metadata'], result)
    return result


def get_ancestor_location_metadata_value(location, metadata_key):
    assert isinstance(location, SQLLocation), type(location)
    for location in reversed(location.get_ancestors(include_self=True)):
        if location.metadata.get(metadata_key):
            return location.metadata[metadata_key]
    return None


def get_case_location(case):
    """
    If the owner of the case is a location, return it. Otherwise return
    the owner's primary location. If the case owner does not have a
    primary location, return None.
    """
    return get_owner_location(case.domain, get_owner_id(case))


def get_owner_location(domain, owner_id):
    owner = get_wrapped_owner(owner_id)
    if not owner:
        return None
    if isinstance(owner, SQLLocation):
        return owner
    location_id = owner.get_location_id(domain)
    return SQLLocation.by_location_id(location_id) if location_id else None
