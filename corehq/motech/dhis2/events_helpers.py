from schema import Optional as SchemaOptional
from schema import Regex, Schema, SchemaError

from corehq.motech.dhis2.const import DHIS2_DATE_SCHEMA, DHIS2_ID_SCHEMA
from corehq.motech.exceptions import ConfigurationError
from corehq.motech.value_source import (
    CaseTriggerInfo,
    get_form_question_values,
)


def send_dhis2_event(request, api_version, form_config, payload):
    event = get_event(request.domain_name, form_config, payload)
    try:
        Schema(get_event_schema()).validate(event)
    except SchemaError as err:
        raise ConfigurationError from err
    return request.post(f'/api/{api_version}/events', json=event,
                        raise_for_status=True)


def get_event(domain, config, form_json=None, info=None):
    if info is None:
        info = CaseTriggerInfo(
            domain=domain,
            case_id=None,
            form_question_values=get_form_question_values(form_json),
        )
    event = {}
    event_property_functions = [
        _get_program,
        _get_program_stage,
        _get_org_unit,
        _get_event_date,
        _get_event_status,
        _get_completed_date,
        _get_datavalues,
    ]
    for func in event_property_functions:
        event.update(func(config, info))
    return event


def _get_program(config, case_trigger_info):
    return {'program': config.program_id}


def _get_program_stage(config, case_trigger_info):
    program_stage_id = None
    if config.program_stage_id:
        program_stage_id = config.program_stage_id.get_value(case_trigger_info)
    if program_stage_id:
        return {'programStage': program_stage_id}
    return {}


def _get_org_unit(config, case_trigger_info):
    org_unit_id = None
    if config.org_unit_id:
        org_unit_id = config.org_unit_id.get_value(case_trigger_info)
    if org_unit_id:
        return {'orgUnit': org_unit_id}
    return {}


def _get_event_date(config, case_trigger_info):
    event_date = config.event_date.get_value(case_trigger_info)
    return {'eventDate': event_date}


def _get_event_status(config, case_trigger_info):
    return {'status': config.event_status}


def _get_completed_date(config, case_trigger_info):
    completed_date = None
    if config.completed_date:
        completed_date = config.completed_date.get_value(case_trigger_info)
    if completed_date:
        return {'completedDate': completed_date}
    return {}


def _get_datavalues(config, case_trigger_info):
    values = []
    for data_value in config.datavalue_maps:
        values.append({
            'dataElement': data_value.data_element_id,
            'value': data_value.value.get_value(case_trigger_info)
        })
    return {'dataValues': values}


def get_event_schema() -> dict:
    """
    Returns the schema for a DHIS2 Event.

    >>> event = {
    ...   "program": "eBAyeGv0exc",
    ...   "orgUnit": "DiszpKrYNg8",
    ...   "eventDate": "2013-05-17",
    ...   "status": "COMPLETED",
    ...   "completedDate": "2013-05-18",
    ...   "storedBy": "admin",
    ...   "coordinate": {
    ...     "latitude": 59.8,
    ...     "longitude": 10.9
    ...   },
    ...   "dataValues": [
    ...     { "dataElement": "qrur9Dvnyt5", "value": "22" },
    ...     { "dataElement": "oZg33kd9taw", "value": "Male" },
    ...     { "dataElement": "msodh3rEMJa", "value": "2013-05-18" }
    ...   ]
    ... }
    >>> Schema(get_event_schema()).is_valid(event)
    True

    """
    return {
        "program": DHIS2_ID_SCHEMA,
        "orgUnit": DHIS2_ID_SCHEMA,
        "eventDate": DHIS2_DATE_SCHEMA,
        SchemaOptional("completedDate"): DHIS2_DATE_SCHEMA,
        SchemaOptional("status"): Regex("^(ACTIVE|COMPLETED|VISITED|SCHEDULE|OVERDUE|SKIPPED)$"),
        SchemaOptional("storedBy"): str,
        SchemaOptional("coordinate"): {
            "latitude": float,
            "longitude": float,
        },
        SchemaOptional("geometry"): {
            "type": str,
            "coordinates": [float],
        },
        SchemaOptional("assignedUser"): DHIS2_ID_SCHEMA,
        "dataValues": [{
            "dataElement": DHIS2_ID_SCHEMA,
            "value": object,
        }],
    }
