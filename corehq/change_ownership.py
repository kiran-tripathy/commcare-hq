import math
import os
from datetime import datetime

from casexml.apps.case.mock import CaseBlock
from dimagi.utils.chunked import chunked

from corehq.apps.es import CaseSearchES
from corehq.apps.es.cases import case_type
from corehq.apps.hqcase.utils import submit_case_blocks
from corehq.apps.locations.models import SQLLocation
from corehq.apps.users.models import CommCareUser
from corehq.form_processor.models import CommCareCase
from corehq.util.log import with_progress_bar

current_time = datetime.now().time()
success_case_log_file_path = os.path.expanduser(f'~/script_success_{current_time}.log') # Use this if we ever need to rollback changes
skipped_log_file_path = os.path.expanduser(f'~/script_skipped_{current_time}.log')
error_log_file_path = os.path.expanduser(f'~/script_error_{current_time}.log')

class Updater(object):
    batch_size = 100  # Could potentially increase this
    domain = 'alafiacomm'
    stat_counts = {
        'success': 0,
        'skipped': 0,
        'failed': 0,
    }

    def write_to_log(self, file_path, ids, message=''):
        with open(file_path, 'a') as log:
            for id in ids:
                log.write(
                    f'{id}' \
                    f' - Reason: {message}' if message else '' \
                    '\n'
                )
            log.close()


class UserUpdater(Updater):
    rc_num_prop_name = 'rc_number'
    user_type_prop_name = 'usertype'

    def start(self):
        print("---MOVING MOBILE WORKER LOCATIONS---")
        users = CommCareUser.by_domain(self.domain)
        user_count = len(users)
        print(f"Total Users to Process: {user_count}")
        for user_chunk in with_progress_bar(chunked(users, self.batch_size), length=user_count, oneline=False):
            users_to_save = self._process_chunk(user_chunk)
            CommCareUser.bulk_save(users_to_save)
            self.write_to_log(
                success_case_log_file_path,
                [u.user_id for u in users_to_save]
            )

        print("Processing Users Complete!")
        print(
            f"Success: {self.stat_counts['success']}, " \
            f"Failed: {self.stat_counts['failed']}, " \
            f"Skipped: {self.stat_counts['skipped']}"
        )

    def _process_chunk(self, user_chunk):
        users_to_save = []
        for user in user_chunk:
            user_data = user.get_user_data(self.domain)

            # First make sure that the user type is rc
            if user_data[self.user_type_prop_name] != 'rc':
                self.write_to_log(
                    skipped_log_file_path,
                    [user.user_id],
                    message='User Type not RC'
                )
                self.stat_counts['skipped'] += 1
                continue     

            try:
                # Get a descendant of user location which has the same rc number
                loc = SQLLocation.objects.get(
                    domain=self.domain,
                    parent__location_id=user.location_id,
                    name=user_data[self.rc_num_prop_name]
                )
            except SQLLocation.DoesNotExist as e:
                self.write_to_log(
                    error_log_file_path,
                    [user.user_id],
                    message=f'({user_data[self.rc_num_prop_name]}) does not exist as child of location with id ({loc.location_id})'
                )
                self.stat_counts['failed'] += 1
                continue

            if loc.location_id == user.location_id:
                # Skip and don't update user if already at location
                self.write_to_log(
                    skipped_log_file_path,
                    [user.user_id],
                    message=f'Skipped as already at RC location with ID {loc.location_id}'
                )
                self.stat_counts['skipped'] += 1
                continue
            else:
                user.location_id = loc.location_id
                self.stat_counts['success'] += 1
                users_to_save.append(user)

        return users_to_save


class CaseUpdater(Updater):
    device_id = 'system'

    def _submit_cases(self, case_blocks):
        submit_case_blocks(
            [cb.as_text() for cb in case_blocks],
            domain=self.domain,
            device_id=self.device_id,
        )

    def start(self):
        print("---MOVING CASE OWNERSHIP---")
        case_ids = (
            CaseSearchES()
            .domain(self.domain)
            .OR(
                case_type('menage'),
                case_type('membre'),
                case_type('seance_educative'),
                case_type('fiche_pointage')
            )
            .sort('opened_on')  # sort so that we can continue
        ).get_ids()

        case_count = len(case_ids)
        batch_count = math.ceil(case_count / self.batch_size)
        print(f'Total Cases to Process: {case_count}')
        print(f'Total Batches to Process: {batch_count}')

        case_gen = CommCareCase.objects.iter_cases(case_ids, domain=self.domain)
        for case_chunk in with_progress_bar(chunked(case_gen, self.batch_size), length=case_count, oneline=False):
            cases_to_save = self._process_chunk(case_chunk)
            self._submit_cases(cases_to_save)

        print("All Cases Done Processing!")
        print(
            f"Successful: {self.stat_counts['success']}, " \
            f"Failed: {self.stat_counts['fail']}, " \
            f"Skipped: {self.stat_counts['skipped']}"
        )

    def _process_chunk(self, case_chunk):
        cases_to_save = []
        for case_obj in case_chunk:
            try:
                user = CommCareUser.get_by_user_id(case_obj.opened_by)
            except CommCareUser.AccountTypeError as e:
                self.write_to_log(
                    skipped_log_file_path,
                    [case_obj.case_id],
                    message='Not owned by a mobile worker'
                )
                self.stat_counts['skipped'] += 1
                continue
            
            if user.location_id == case_obj.owner_id:
                # Skip and don't update case if already owned by location
                self.write_to_log(
                    skipped_log_file_path,
                    [case_obj.case_id],
                    message='Already owned by correct location'
                )
                self.stat_counts['skipped'] += 1
                continue

            case_block = CaseBlock(
                create=False,
                case_id=case_obj.case_id,
                owner_id=user.location_id,
            )
            cases_to_save.append(case_block)

        return cases_to_save
