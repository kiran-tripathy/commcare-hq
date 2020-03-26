from collections import defaultdict

from django.utils.functional import cached_property

from corehq.apps.locations.models import LocationType, SQLLocation
from custom.icds.location_reassignment.const import (
    EXTRACT_OPERATION,
    MERGE_OPERATION,
    MOVE_OPERATION,
    NEW_SITE_CODE_COLUMN,
    OLD_SITE_CODE_COLUMN,
    OPERATION_COLUMN,
    SPLIT_OPERATION,
    VALID_OPERATIONS,
)
from custom.icds.location_reassignment.utils import deprecate_locations


class Parser(object):
    def __init__(self, domain, workbook):
        """
        Receives a worksheet generated by custom.icds.location_reassignment.download.Download
        and generates an output like
        {
            location_type_code:
                'Merge': {
                    'New location site code': ['Old location site code', 'Old location site code']
                },
                'Split': {
                    'Old location site code': ['New location site code', 'New location site code']
                },
                'Rename': {
                    'New location site code': 'Old location site code'
                },
                'Extract': {
                    'New location site code': 'Old location site code'
                }
        }
        """
        self.domain = domain
        self.workbook = workbook
        # mapping each location code to the type of operation requested for it
        self.requested_transitions = {}
        self.site_codes_to_be_archived = []
        self.valid_transitions = {location_type_code: {
            MERGE_OPERATION: defaultdict(list),
            SPLIT_OPERATION: defaultdict(list),
            MOVE_OPERATION: {},
            EXTRACT_OPERATION: {},
        } for location_type_code in self.location_type_codes}
        self.errors = []

    @cached_property
    def location_type_codes(self):
        return [lt.code for lt in LocationType.objects.by_domain()]

    def parse(self):
        for worksheet in self.workbook.worksheets:
            location_type_code = worksheet.title
            for row in worksheet:
                operation = row.get(OPERATION_COLUMN)
                if not operation:
                    continue
                if operation not in VALID_OPERATIONS:
                    self.errors.append("Invalid Operation %s" % operation)
                    continue
                self._parse_row(row, location_type_code)
        self.validate()
        return self.valid_transitions, self.errors

    def _parse_row(self, row, location_type_code):
        operation = row.get(OPERATION_COLUMN)
        old_site_code = row.get(OLD_SITE_CODE_COLUMN)
        new_site_code = row.get(NEW_SITE_CODE_COLUMN)
        if not old_site_code or not new_site_code:
            self.errors.append("Missing location code for %s, got old: '%s' and new: '%s'" % (
                operation, old_site_code, new_site_code
            ))
            return
        if old_site_code == new_site_code:
            self.errors.append("No change in location code for %s, got old: '%s' and new: '%s'" % (
                operation, old_site_code, new_site_code
            ))
            return
        if self._invalid_row(operation, old_site_code, new_site_code):
            return
        self._note_transition(operation, location_type_code, new_site_code, old_site_code)

    def _invalid_row(self, operation, old_site_code, new_site_code):
        invalid = False
        if old_site_code in self.requested_transitions:
            if self.requested_transitions.get(old_site_code) != operation:
                self.errors.append("Multiple transitions for %s, %s and %s" % (
                    old_site_code, self.requested_transitions.get(old_site_code), operation))
                invalid = True
        if new_site_code in self.requested_transitions:
            if self.requested_transitions.get(new_site_code) != operation:
                self.errors.append("Multiple transitions for %s, %s and %s" % (
                    new_site_code, self.requested_transitions.get(new_site_code), operation))
                invalid = True
        return invalid

    def _note_transition(self, operation, location_type_code, new_site_code, old_site_code):
        if operation == MERGE_OPERATION:
            self.valid_transitions[location_type_code][operation][new_site_code].append(old_site_code)
        elif operation == SPLIT_OPERATION:
            self.valid_transitions[location_type_code][operation][old_site_code].append(new_site_code)
        elif operation == MOVE_OPERATION:
            self.valid_transitions[location_type_code][operation][new_site_code] = old_site_code
        elif operation == EXTRACT_OPERATION:
            self.valid_transitions[location_type_code][operation][new_site_code] = old_site_code
        self.site_codes_to_be_archived.append(old_site_code)
        self.requested_transitions[old_site_code] = operation
        self.requested_transitions[new_site_code] = operation

    def validate(self):
        if self.site_codes_to_be_archived:
            self._validate_descendants_archived()

    def _validate_descendants_archived(self):
        """
        ensure all locations getting archived, also have their descendants getting archived
        """
        site_codes_to_be_archived = set(self.site_codes_to_be_archived)
        locations_to_be_archived = SQLLocation.active_objects.filter(site_code__in=self.site_codes_to_be_archived)
        for location in locations_to_be_archived:
            descendants_sites_codes = location.get_descendants().values_list('site_code', flat=True)
            missing_site_codes = set(descendants_sites_codes) - site_codes_to_be_archived
            if missing_site_codes:
                self.errors.append("Location %s is getting archived but the following descendants are not %s" % (
                    location.location_id, ",".join(missing_site_codes)
                ))

    def process(self):
        # process each sheet, in reverse order of hierarchy
        for location_type_code in list(reversed(self.location_type_codes)):
            for operation, transitions in self.valid_transitions[location_type_code].items():
                self._perform_transitions(operation, transitions)

    def _perform_transitions(self, operation, transitions):
        for old_site_codes, new_site_codes in transitions.items():
            deprecate_locations(operation, self._get_locations(old_site_codes),
                                self._get_locations(new_site_codes))

    def _get_locations(self, site_codes):
        site_codes = site_codes if isinstance(site_codes, list) else [site_codes]
        locations = [self.locations_by_site_code[site_code] for site_code in site_codes]
        assert len(locations), len(site_codes)
        return locations

    @cached_property
    def locations_by_site_code(self):
        return {
            loc.site_code: loc
            for loc in SQLLocation.active_objects.filter(site_code__in=self.requested_transitions.keys())
        }
