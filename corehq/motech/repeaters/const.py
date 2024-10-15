from datetime import timedelta
from django.utils.translation import gettext_lazy as _

from django.conf import settings
from django.db.models import IntegerChoices

MAX_RETRY_WAIT = timedelta(days=7)
MIN_RETRY_WAIT = timedelta(minutes=60)
RATE_LIMITER_DELAY_RANGE = (
    timedelta(minutes=getattr(settings, 'MIN_REPEATER_RATE_LIMIT_DELAY', 0)),
    timedelta(minutes=getattr(settings, 'MAX_REPEATER_RATE_LIMIT_DELAY', 15)),
)
CHECK_REPEATERS_INTERVAL = timedelta(minutes=5)
CHECK_REPEATERS_KEY = 'check-repeaters-key'
PROCESS_REPEATERS_INTERVAL = timedelta(minutes=1)
PROCESS_REPEATERS_KEY = 'process-repeaters-key'
ENDPOINT_TIMER = 'endpoint_timer'
# Number of attempts to an online endpoint before cancelling payload
MAX_ATTEMPTS = 3
# Number of exponential backoff attempts to an offline endpoint
MAX_BACKOFF_ATTEMPTS = 6
# Minutes past next_check time that make a record "overdue"
OVERDUE_THRESHOLD = 10


class State(IntegerChoices):
    # powers of two to allow multiple simultaneous states (not currently used)
    Pending = 1, _('Pending')
    Fail = 2, _('Failed')  # Will be retried. Implies Pending.
    Success = 4, _('Succeeded')
    Cancelled = 8, _('Cancelled')
    Empty = 16, _('Empty')  # There was nothing to send. Implies Success.
    InvalidPayload = 32, _('Invalid Payload')  # Implies Cancelled.


RECORD_PENDING_STATE = State.Pending
RECORD_SUCCESS_STATE = State.Success
RECORD_FAILURE_STATE = State.Fail
RECORD_CANCELLED_STATE = State.Cancelled
RECORD_EMPTY_STATE = State.Empty
RECORD_INVALIDPAYLOAD_STATE = State.InvalidPayload


class UCRRestrictionFFStatus(IntegerChoices):
    Enabled = 1, _('Is enabled')
    NotEnabled = 2, _('Is not enabled')
    ShouldEnable = 3, _('Should be enabled')
    CanDisable = 4, _('Can be disabled')
