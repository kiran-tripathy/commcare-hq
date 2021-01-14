from datetime import datetime, timedelta

from django.conf import settings

from celery.schedules import crontab
from celery.task import periodic_task, task
from celery.utils.log import get_task_logger

from dimagi.utils.couch import get_redis_lock
from dimagi.utils.couch.undo import DELETED_SUFFIX

from corehq.motech.models import RequestLog
from corehq.util.metrics import (
    make_buckets_from_timedeltas,
    metrics_counter,
    metrics_gauge_task,
    metrics_histogram_timer,
)
from corehq.util.metrics.const import MPM_MAX
from corehq.util.soft_assert import soft_assert

from .const import (
    CHECK_REPEATERS_INTERVAL,
    CHECK_REPEATERS_KEY,
    MAX_RETRY_WAIT,
    RECORD_FAILURE_STATE,
    RECORD_PENDING_STATE,
)
from .dbaccessors import (
    get_overdue_repeat_record_count,
    iterate_repeat_records,
)
from .models import domain_can_forward

_check_repeaters_buckets = make_buckets_from_timedeltas(
    timedelta(seconds=10),
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(hours=1),
    timedelta(hours=5),
    timedelta(hours=10),
)
MOTECH_DEV = '@'.join(('nhooper', 'dimagi.com'))
_soft_assert = soft_assert(to=MOTECH_DEV)
logging = get_task_logger(__name__)


@periodic_task(
    run_every=crontab(day_of_month=27),
    queue=settings.CELERY_PERIODIC_QUEUE,
)
def clean_logs():
    """
    Drop MOTECH logs older than 90 days.

    Runs on the 27th of every month.
    """
    ninety_days_ago = datetime.now() - timedelta(days=90)
    RequestLog.objects.filter(timestamp__lt=ninety_days_ago).delete()


@periodic_task(
    run_every=CHECK_REPEATERS_INTERVAL,
    queue=settings.CELERY_PERIODIC_QUEUE,
)
def check_repeaters():
    start = datetime.utcnow()
    twentythree_hours_sec = 23 * 60 * 60
    twentythree_hours_later = start + timedelta(hours=23)

    # Long timeout to allow all waiting repeat records to be iterated
    check_repeater_lock = get_redis_lock(
        CHECK_REPEATERS_KEY,
        timeout=twentythree_hours_sec,
        name=CHECK_REPEATERS_KEY,
    )
    if not check_repeater_lock.acquire(blocking=False):
        metrics_counter("commcare.repeaters.check.locked_out")
        return

    try:
        with metrics_histogram_timer(
            "commcare.repeaters.check.processing",
            timing_buckets=_check_repeaters_buckets,
        ):
            for record in iterate_repeat_records(start):
                if not _soft_assert(
                    datetime.utcnow() < twentythree_hours_later,
                    "I've been iterating repeat records for 23 hours. I quit!"
                ):
                    break
                metrics_counter("commcare.repeaters.check.attempt_forward")
                record.attempt_forward_now()
            else:
                iterating_time = datetime.utcnow() - start
                _soft_assert(
                    iterating_time < timedelta(hours=6),
                    f"It took {iterating_time} to iterate repeat records."
                )
    finally:
        check_repeater_lock.release()


@task(serializer='pickle', queue=settings.CELERY_REPEAT_RECORD_QUEUE)
def process_repeat_record(repeat_record):

    # A RepeatRecord should ideally never get into this state, as the
    # domain_has_privilege check is also triggered in the create_repeat_records
    # in signals.py. But if it gets here, forcefully cancel the RepeatRecord.
    if not domain_can_forward(repeat_record.domain):
        repeat_record.cancel()
        repeat_record.save()

    if (
        repeat_record.state == RECORD_FAILURE_STATE and
        repeat_record.overall_tries >= repeat_record.max_possible_tries
    ):
        repeat_record.cancel()
        repeat_record.save()
        return
    if repeat_record.cancelled:
        return

    repeater = repeat_record.repeater
    if not repeater:
        repeat_record.cancel()
        repeat_record.save()
        return

    try:
        if repeater.paused:
            # postpone repeat record by 1 day so that these don't get picked in each cycle and
            # thus clogging the queue with repeat records with paused repeater
            repeat_record.postpone_by(MAX_RETRY_WAIT)
            return

        if repeater.doc_type.endswith(DELETED_SUFFIX):
            if not repeat_record.doc_type.endswith(DELETED_SUFFIX):
                repeat_record.doc_type += DELETED_SUFFIX
                repeat_record.save()
        elif repeat_record.state == RECORD_PENDING_STATE or repeat_record.state == RECORD_FAILURE_STATE:
                repeat_record.fire()
    except Exception:
        logging.exception('Failed to process repeat record: {}'.format(repeat_record._id))


repeaters_overdue = metrics_gauge_task(
    'commcare.repeaters.overdue',
    get_overdue_repeat_record_count,
    run_every=crontab(),  # every minute
    multiprocess_mode=MPM_MAX
)
