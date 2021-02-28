import json
import os
from itertools import zip_longest
from typing import Optional, Union

from django.conf import settings
from django.db import models

from jsonfield import JSONField
from jsonschema import RefResolver, ValidationError, validate

from casexml.apps.case.models import CommCareCase

from corehq.apps.data_dictionary.models import CaseProperty, CaseType
from corehq.apps.data_dictionary.util import get_case_type_obj
from corehq.form_processor.models import CommCareCaseSQL
from corehq.motech.exceptions import ConfigurationError
from corehq.motech.value_source import (
    CaseTriggerInfo,
    ValueSource,
    as_value_source,
)
from corehq.motech.fhir import serializers  # noqa # pylint: disable=unused-import

from .const import FHIR_VERSION_4_0_1, FHIR_VERSIONS


class FHIRResourceType(models.Model):
    domain = models.CharField(max_length=127, db_index=True)
    fhir_version = models.CharField(max_length=12, choices=FHIR_VERSIONS,
                                    default=FHIR_VERSION_4_0_1)
    case_type = models.ForeignKey(CaseType, on_delete=models.CASCADE)

    # For a list of resource types, see http://hl7.org/fhir/resourcelist.html
    name = models.CharField(max_length=255)

    # `template` offers a way to define a FHIR resource if it cannot be
    # built using only mapped case properties.
    template = JSONField(default=dict)

    class Meta:
        unique_together = ('case_type', 'fhir_version')

    def __str__(self):
        return self.name

    def get_json_schema(self) -> dict:
        """
        Returns the JSON schema of this resource type.

        >>> resource_type = FHIRResourceType(
        ...     case_type=CaseType(name='mother'),
        ...     name='Patient',
        ... )
        >>> schema = resource_type.get_json_schema()
        >>> schema['$ref']
        '#/definitions/Patient'

        """
        try:
            with open(self._schema_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            raise ConfigurationError(
                f'Unknown resource type {self.name!r} for FHIR version '
                f'{self.fhir_version}'
            )

    @classmethod
    def get_names(cls, version=FHIR_VERSION_4_0_1):
        schema_dir = get_schema_dir(version)
        ext = len('.schema.json')
        return [n[:-ext] for n in os.listdir(schema_dir)]

    def validate_resource(self, fhir_resource):
        schema = self.get_json_schema()
        resolver = RefResolver(base_uri=f'file://{self._schema_file}',
                               referrer=schema)
        try:
            validate(fhir_resource, schema, resolver=resolver)
        except ValidationError as err:
            raise ConfigurationError(
                f'Validation failed for resource {fhir_resource!r}: {err}'
            ) from err

    @property
    def _schema_file(self):
        return os.path.join(self._schema_dir, f'{self.name}.schema.json')

    @property
    def _schema_dir(self):
        return get_schema_dir(self.fhir_version)


def get_schema_dir(version):
    ver = dict(FHIR_VERSIONS)[version].lower()
    return os.path.join(settings.BASE_DIR, 'corehq', 'motech', 'fhir',
                        'json-schema', ver)


class FHIRResourceProperty(models.Model):
    resource_type = models.ForeignKey(FHIRResourceType,
                                      on_delete=models.CASCADE,
                                      related_name='properties')

    # `case_property`, `jsonpath` and `value_map` are set using the
    # Data Dictionary UI.
    case_property = models.ForeignKey(CaseProperty, on_delete=models.SET_NULL,
                                      null=True, blank=True, default=None)
    # Path to the FHIR resource property that corresponds with `case_property`
    jsonpath = models.TextField(null=True, blank=True, default=None)
    # Optional[dict] {CommCare value: FHIR value}
    value_map = JSONField(null=True, blank=True, default=None)

    # `value_source_config` is used when the Data Dictionary UI cannot
    # do what you need.
    value_source_config = JSONField(null=True, blank=True, default=None)

    def save(self, *args, **kwargs):
        if (
            self.case_property
            and self.case_property.case_type != self.resource_type.case_type
        ):
            raise ConfigurationError(
                "Invalid FHIRResourceProperty: case_property case type "
                f"'{self.case_property.case_type}' does not match "
                f"resource_type case type '{self.resource_type.case_type}'.")
        if (
            (self.case_property or self.jsonpath or self.value_map)
            and self.value_source_config
        ):
            raise ConfigurationError(
                "Invalid FHIRResourceProperty: Unable to set "
                "'value_source_config' when 'case_property', 'jsonpath' or "
                "'value_map' are set.")
        super().save(*args, **kwargs)

    @property
    def case_type(self) -> CaseType:
        return self.resource_type.case_type

    @property
    def case_property_name(self) -> Optional[str]:
        if self.case_property:
            return self.case_property.name
        if (
            self.value_source_config
            and 'case_property' in self.value_source_config
        ):
            return self.value_source_config['case_property']
        return None

    def get_value_source(self) -> ValueSource:
        """
        Returns a ValueSource for building FHIR resources.
        """
        if self.value_source_config:
            return as_value_source(self.value_source_config)

        if not (self.case_property and self.jsonpath):
            raise ConfigurationError(
                'Unable to set FHIR resource property value without case '
                'property and JSONPath.')
        value_source_config = {
            'case_property': self.case_property.name,
            'jsonpath': self.jsonpath,
        }
        if self.value_map:
            value_source_config['value_map'] = self.value_map
        return as_value_source(value_source_config)


def build_fhir_resource(
    case: Union[CommCareCase, CommCareCaseSQL],
    fhir_version: str = FHIR_VERSION_4_0_1,
) -> Optional[dict]:
    """
    Builds a FHIR resource using data from ``case``. Returns ``None`` if
    mappings do not exist.

    Used by the FHIR API.
    """
    try:
        info = get_case_trigger_info(case)
    except AssertionError:
        return None
    return _build_fhir_resource(info, fhir_version)


def build_fhir_resource_for_info(
    info: CaseTriggerInfo,
    fhir_version: str,
) -> Optional[dict]:
    """
    Builds a FHIR resource using data from ``info``. Returns ``None`` if
    mappings do not exist, or if there is no data to forward.

    Used by ``FHIRRepeater``.
    """
    return _build_fhir_resource(info, fhir_version, skip_empty=True)


def _build_fhir_resource(
    info: CaseTriggerInfo,
    fhir_version: str,
    *,
    skip_empty: bool = False,
) -> Optional[dict]:

    case_type = get_case_type_obj(info.domain, info.type)
    if not case_type:
        return None

    try:
        resource_type = (
            FHIRResourceType.objects
            .prefetch_related('properties__case_property')
            .get(case_type=case_type, fhir_version=fhir_version)
        )
    except FHIRResourceType.DoesNotExist:
        return None

    fhir_resource = {}
    for prop in resource_type.properties.all():
        value_source = prop.get_value_source()
        value_source.set_external_value(fhir_resource, info)
    if not fhir_resource and skip_empty:
        return None

    fhir_resource = deepmerge({
        **resource_type.template,
        'id': info.case_id,
        'resourceType': resource_type.name,  # Always required
    }, fhir_resource)
    resource_type.validate_resource(fhir_resource)
    return fhir_resource


def get_case_trigger_info(
    case: Union[CommCareCase, CommCareCaseSQL],
    case_block: Optional[dict] = None,
    form_question_values: Optional[dict] = None,
) -> CaseTriggerInfo:
    """
    Returns ``CaseTriggerInfo`` instance for ``case``.

    Ignores case properties that aren't in the Data Dictionary.

    ``CaseTriggerInfo`` packages case (and form) data for use by
    ``ValueSource``.
    """
    if case_block is None:
        case_block = {}
    else:
        assert case_block['@case_id'] == case.case_id
    if form_question_values is None:
        form_question_values = {}

    case_create = case_block.get('create') or {}
    case_update = case_block.get('update') or {}

    case_type = get_case_type_obj(case.domain, case.type)
    assert case_type, f'CaseType not found for case type {case.type!r}'
    prop_names = [p.name for p in case_type.properties.all()]
    extra_fields = {p: case.get_case_property(p) for p in prop_names}
    # Include external_id because `get_bundle_entries()` uses it
    # to determine whether to PUT or POST.
    extra_fields['external_id'] = case.get_case_property('external_id')

    return CaseTriggerInfo(
        domain=case.domain,
        case_id=case.case_id,
        type=case.type,
        name=case.name,
        owner_id=case.owner_id,
        modified_by=case.modified_by,
        updates={**case_create, **case_update},
        created='create' in case_block if case_block else None,
        closed='close' in case_block if case_block else None,
        extra_fields=extra_fields,
        form_question_values=form_question_values,
    )


def deepmerge(a, b):
    """
    Merges ``b`` into ``a``.

    >>> foo = {'one': {'two': 2, 'three': 42}}
    >>> bar = {'one': {'three': 3}}
    >>> {**foo, **bar}
    {'one': {'three': 3}}
    >>> deepmerge(foo, bar)
    {'one': {'two': 2, 'three': 3}}

    Dicts and lists are recursed. Other data types are replaced.

    >>> foo = {'one': [{'two': 2}, 42]}
    >>> bar = {'one': [{'three': 3}]}
    >>> deepmerge(foo, bar)
    {'one': [{'two': 2, 'three': 3}, 42]}

    """
    if isinstance(a, dict) and isinstance(b, dict):
        for key in b:
            if key in a:
                a[key] = deepmerge(a[key], b[key])
            else:
                a[key] = b[key]
        return a
    elif isinstance(a, list) and isinstance(b, list):
        return list(deepmerge(aa, bb) for aa, bb in zip_longest(a, b))
    elif b is None:
        return a
    else:
        return b
