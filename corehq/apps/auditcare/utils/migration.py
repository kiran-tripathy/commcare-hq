import logging

from datetime import datetime, timedelta

from django.core.cache import cache

from dimagi.utils.dates import force_to_datetime

from corehq.apps.auditcare.models import AuditcareMigrationMeta
from corehq.apps.auditcare.utils.export import get_sql_start_date

CUTOFF_TIME = datetime(2021, 2, 1)
CACHE_TTL = 14 * 24 * 60 * 60  # 14 days

logger = logging.getLogger(__name__)


class AuditCareMigrationUtil():

    def __init__(self):
        self.start_key = "auditcare_migration_2021_next_batch_time"
        self.start_lock_key = "auditcare_migration_batch_lock"

    def get_next_batch_start(self):
        return cache.get(self.start_key)

    def generate_batches(self, worker_count, batch_by):
        batches = []
        with cache.lock(self.start_lock_key, timeout=10):
            start_datetime = self.get_next_batch_start()
            if not start_datetime:
                if AuditcareMigrationMeta.objects.count() != 0:
                    raise MissingStartTimeError()
                # For first run set the start_datetime to the event_time of the first record
                # in the SQL. If there are no records in SQL, start_time would be set as
                # current time
                start_datetime = get_sql_start_date()
                if not start_datetime:
                    start_datetime = datetime.now()

            if start_datetime < CUTOFF_TIME:
                logger.info("Migration Successfull")
                return

            start_time = start_datetime
            end_time = None

            for index in range(worker_count):
                end_time = _get_end_time(start_time, batch_by)
                if end_time < CUTOFF_TIME:
                    break
                batches.append([start_time, end_time])
                start_time = end_time
            self.set_next_batch_start(end_time)

        return batches

    def set_next_batch_start(self, value):
        cache.set(self.start_key, value, CACHE_TTL)

    def get_errored_keys(self, limit):
        errored_keys = (AuditcareMigrationMeta.objects
            .filter(state=AuditcareMigrationMeta.ERRORED)
            .values_list('key', flat=True)[:limit])

        return [get_datetimes_from_key(key) for key in errored_keys]

    def log_batch_start(self, key):
        if AuditcareMigrationMeta.objects.filter(key=key):
            return
        AuditcareMigrationMeta.objects.create(key=key, state=AuditcareMigrationMeta.STARTED, record_count=0)

    def set_batch_as_finished(self, key, count):
        AuditcareMigrationMeta.objects.filter(key=key).update(
            state=AuditcareMigrationMeta.FINISHED,
            record_count=count
        )

    def set_batch_as_errored(self, key):
        AuditcareMigrationMeta.objects.filter(key=key).update(state=AuditcareMigrationMeta.ERRORED)

    def get_existing_count(self, key):
        return AuditcareMigrationMeta.objects.filter(key=key).values_list('record_count', flat=True).first() or 0


def get_formatted_datetime_string(datetime_obj):
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")


def get_datetimes_from_key(key):
    start, end = key.split("_")
    return [force_to_datetime(start), force_to_datetime(end)]


def _get_end_time(start_time, batch_by):
    delta = timedelta(hours=1) if batch_by == 'h' else timedelta(days=1)
    end_time = start_time - delta
    if batch_by == 'h':
        return end_time.replace(minute=0, second=0, microsecond=0)
    else:
        return end_time.replace(hour=0, minute=0, second=0, microsecond=0)


class MissingStartTimeError(Exception):
    message = """The migration process has already been started before
        But we are unable to determine start key.
        You can manually set the start key using
        start_key = "2021-06-02_2021-06-01"
        AuditCareMigraionUtil.set_next_batch_start(start_key)"""

    def __init__(self, message=message):
        super().__init__(message)
