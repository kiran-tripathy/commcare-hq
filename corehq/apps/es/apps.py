"""
AppES
-----
"""
from datetime import datetime

from dimagi.utils.parsing import json_format_datetime

from . import filters, queries
from .client import ElasticDocumentAdapter, create_document_adapter
from .es_query import HQESQuery
from .index.settings import IndexSettingsKey
from .transient_util import get_adapter_mapping


class AppES(HQESQuery):
    index = 'apps'

    @property
    def builtin_filters(self):
        return [
            is_build,
            is_released,
            created_from_template,
            uses_case_sharing,
            cloudcare_enabled,
            app_id,
        ] + super(AppES, self).builtin_filters


class ElasticApp(ElasticDocumentAdapter):

    settings_key = IndexSettingsKey.APPS

    @property
    def mapping(self):
        return get_adapter_mapping(self)

    @property
    def model_cls(self):
        from corehq.apps.app_manager.models import ApplicationBase
        return ApplicationBase

    def _from_dict(self, app_dict):
        app_dict['@indexed_on'] = json_format_datetime(datetime.utcnow())
        return super()._from_dict(app_dict)


app_adapter = create_document_adapter(
    ElasticApp,
    "hqapps_2020-02-26",
    "app",
)


def build_comment(comment):
    return queries.search_string_query(comment, ['build_comment'])


def version(version):
    return filters.term('version', version)


def is_build(build=True):
    filter = filters.empty('copy_of')
    if build:
        return filters.NOT(filter)
    return filter


def is_released(released=True):
    return filters.term('is_released', released)


def created_from_template(from_template=True):
    filter = filters.empty('created_from_template')
    if from_template:
        return filters.NOT(filter)
    return filter


def uses_case_sharing(case_sharing=True):
    return filters.term('case_sharing', case_sharing)


def cloudcare_enabled(cloudcare_enabled):
    return filters.term('cloudcare_enabled', cloudcare_enabled)


def app_id(app_id):
    return filters.term('copy_of', app_id)
