from django.utils.translation import ugettext_lazy as _

BASIC_AUTH = "basic"
DIGEST_AUTH = "digest"
OAUTH1 = "oauth1"
BEARER_AUTH = "bearer"
OAUTH2_PWD = "oauth2_pwd"
AUTH_TYPES = (
    (BASIC_AUTH, "HTTP Basic"),
    (DIGEST_AUTH, "HTTP Digest"),
    (BEARER_AUTH, "Bearer Token"),
    (OAUTH1, "OAuth1"),
    (OAUTH2_PWD, "OAuth 2.0 Password Grant")
)

PASSWORD_PLACEHOLDER = '*' * 16

CONNECT_TIMEOUT = 60
# If any remote service does not respond within 5 minutes, time out.
# (Some OpenMRS reports can take a long time. Cut them a little slack,
# but not too much.)
READ_TIMEOUT = 5 * 60
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

ALGO_AES = 'aes'

IMPORT_FREQUENCY_DAILY = 'daily'
IMPORT_FREQUENCY_WEEKLY = 'weekly'
IMPORT_FREQUENCY_MONTHLY = 'monthly'
IMPORT_FREQUENCY_CHOICES = (
    (IMPORT_FREQUENCY_DAILY, _('Daily')),
    (IMPORT_FREQUENCY_WEEKLY, _('Weekly')),
    (IMPORT_FREQUENCY_MONTHLY, _('Monthly')),
)

DATA_TYPE_UNKNOWN = None

COMMCARE_DATA_TYPE_TEXT = 'cc_text'
COMMCARE_DATA_TYPE_INTEGER = 'cc_integer'
COMMCARE_DATA_TYPE_DECIMAL = 'cc_decimal'
COMMCARE_DATA_TYPE_BOOLEAN = 'cc_boolean'
COMMCARE_DATA_TYPE_DATE = 'cc_date'
COMMCARE_DATA_TYPE_DATETIME = 'cc_datetime'
COMMCARE_DATA_TYPE_TIME = 'cc_time'
COMMCARE_DATA_TYPES = (
    COMMCARE_DATA_TYPE_TEXT,
    COMMCARE_DATA_TYPE_INTEGER,
    COMMCARE_DATA_TYPE_DECIMAL,
    COMMCARE_DATA_TYPE_BOOLEAN,
    COMMCARE_DATA_TYPE_DATE,
    COMMCARE_DATA_TYPE_DATETIME,
    COMMCARE_DATA_TYPE_TIME,
)
COMMCARE_DATA_TYPES_AND_UNKNOWN = COMMCARE_DATA_TYPES + (DATA_TYPE_UNKNOWN,)

DIRECTION_IMPORT = 'in'
DIRECTION_EXPORT = 'out'
DIRECTION_BOTH = None
DIRECTIONS = (
    DIRECTION_IMPORT,
    DIRECTION_EXPORT,
    DIRECTION_BOTH,
)
