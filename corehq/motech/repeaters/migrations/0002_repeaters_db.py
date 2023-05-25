# Generated by Django 3.2.16 on 2023-04-12 20:05
#
# This migration assumes that repeaters_repeatrecord and
# repeaters_repeatrecordattempt tables are not in use.

from django.conf import settings
from django.db import migrations
from django.db.utils import DEFAULT_DB_ALIAS

MOVE_TO_SEPARATE_DB = """
    CREATE SERVER repeaters_fdw FOREIGN DATA WRAPPER postgres_fdw
        OPTIONS (host '{HOST}', port '{PORT}', dbname '{NAME}');
    CREATE USER MAPPING FOR {USER} SERVER repeaters_fdw
        OPTIONS (user '{USER}', password '{PASSWORD}');
    GRANT USAGE ON FOREIGN SERVER repeaters_fdw TO {USER};

    DROP TABLE repeaters_repeatrecordattempt;
    DROP TABLE repeaters_repeatrecord;
    LOCK TABLE repeaters_repeater IN SHARE ROW EXCLUSIVE mode;
    ALTER TABLE repeaters_repeater RENAME TO repeaters_repeater_old;
    IMPORT FOREIGN SCHEMA public LIMIT TO ("repeaters_repeater", "repeaters_repeatrecord")
        FROM SERVER repeaters_fdw INTO public;
    INSERT INTO repeaters_repeater SELECT * FROM repeaters_repeater_old;
    DROP TABLE repeaters_repeater_old;
"""

# NOTE this does not copy data in repeaters_repeatrecord and
# repeaters_repeatrecordattempt from the foreign tables. Those tables are
# expected to contain no data when the forward migration is performed,
# and that state will be preserved if the migration is reversed. If they
# did contain data it would likely be too much to copy in a single
# database transaction, and locking the table in the foreign database is
# not possible from here anyway.
#
# In case it was not clear, this is not a safe migration to run if there
# are any active writers on the foreign table(s).
UNDO_MOVE_TO_SEPARATE_DB = """
    IMPORT FOREIGN SCHEMA public
        LIMIT TO (repeaters_repeatrecord, repeaters_repeatrecordattempt)
        FROM SERVER repeaters_fdw INTO public;

    ALTER TABLE repeaters_repeater RENAME TO repeaters_repeater_old;
    CREATE TABLE repeaters_repeater (LIKE repeaters_repeater_old INCLUDING ALL);
    ALTER TABLE repeaters_repeater ADD PRIMARY KEY (id); -- TODO should be named repeaters_repeater_pkey
    INSERT INTO repeaters_repeater SELECT * FROM repeaters_repeater_old;
    CREATE SEQUENCE repeaters_repeater_id_seq
        INCREMENT 1 MINVALUE 1 CACHE 1 MAXVALUE 2147483648 START 1
        OWNED BY public.repeaters_repeater.id;
    SELECT setval('repeaters_repeater_id_seq', (SELECT MAX(id) + 1 FROM repeaters_repeater), true);
    ALTER TABLE repeaters_repeater
        ALTER COLUMN id SET DEFAULT nextval('repeaters_repeater_id_seq'::regclass);
    CREATE INDEX IF NOT EXISTS repeaters_repeater_connection_settings_id_fb1a9503
        ON repeaters_repeater (connection_settings_id);
    CREATE INDEX IF NOT EXISTS repeaters_repeater_domain_b537389f
        ON repeaters_repeater (domain);
    CREATE INDEX IF NOT EXISTS repeaters_repeater_domain_b537389f_like
        ON repeaters_repeater (domain varchar_pattern_ops);
    CREATE INDEX IF NOT EXISTS repeaters_repeater_is_deleted_08441bf0
        ON repeaters_repeater (is_deleted);
    CREATE INDEX IF NOT EXISTS repeaters_repeater_repeater_id_9ab445dc_like
        ON repeaters_repeater (repeater_id varchar_pattern_ops);
    ALTER TABLE repeaters_repeater ADD CONSTRAINT repeaters_repeater_repeater_id_9ab445dc_uniq
        UNIQUE (repeater_id);

    ALTER TABLE repeaters_repeatrecord RENAME TO repeaters_repeatrecord_old;
    CREATE TABLE repeaters_repeatrecord (LIKE repeaters_repeatrecord_old INCLUDING ALL);
    ALTER TABLE repeaters_repeatrecord ADD PRIMARY KEY (id);
    CREATE SEQUENCE repeaters_repeatrecord_id_seq
        INCREMENT 1 MINVALUE 1 CACHE 1 MAXVALUE 2147483648 START 1
        OWNED BY public.repeaters_repeatrecord.id;
    ALTER TABLE repeaters_repeatrecord
        ALTER COLUMN id SET DEFAULT nextval('repeaters_repeatrecord_id_seq'::regclass);
    CREATE INDEX IF NOT EXISTS repeaters_r_couch_i_ea5782_idx
        ON repeaters_repeatrecord (couch_id);
    CREATE INDEX IF NOT EXISTS repeaters_r_domain_3ae9ab_idx
        ON repeaters_repeatrecord (domain);
    CREATE INDEX IF NOT EXISTS repeaters_r_payload_f64556_idx
        ON repeaters_repeatrecord (payload_id);
    CREATE INDEX IF NOT EXISTS repeaters_r_registe_b48c68_idx
        ON repeaters_repeatrecord (registered_at);
    CREATE INDEX IF NOT EXISTS repeaters_repeatrecord_repeater_id_01b51f9d
        ON repeaters_repeatrecord (repeater_id);
    ALTER TABLE repeaters_repeatrecord
        ADD CONSTRAINT repeaters_repeatreco_repeater_id_01b51f9d_fk_repeaters
        FOREIGN KEY (repeater_id) REFERENCES repeaters_repeater(id) DEFERRABLE INITIALLY DEFERRED;

    ALTER TABLE repeaters_repeatrecordattempt RENAME TO repeaters_repeatrecordattempt_old;
    CREATE TABLE repeaters_repeatrecordattempt (LIKE repeaters_repeatrecordattempt_old INCLUDING ALL);
    ALTER TABLE repeaters_repeatrecordattempt ADD PRIMARY KEY (id);
    CREATE SEQUENCE repeaters_repeatrecordattempt_id_seq
        INCREMENT 1 MINVALUE 1 CACHE 1 MAXVALUE 2147483648 START 1
        OWNED BY public.repeaters_repeatrecordattempt.id;
    ALTER TABLE repeaters_repeatrecordattempt
        ALTER COLUMN id SET DEFAULT nextval('repeaters_repeatrecordattempt_id_seq'::regclass);
    CREATE INDEX IF NOT EXISTS repeaters_repeatrecordattempt_repeat_record_id_cc88c323
        ON repeaters_repeatrecordattempt (repeat_record_id);
    ALTER TABLE repeaters_repeatrecordattempt
        ADD CONSTRAINT repeaters_repeatreco_repeat_record_id_cc88c323_fk_repeaters
        FOREIGN KEY (repeat_record_id) REFERENCES repeaters_repeatrecord(id) DEFERRABLE INITIALLY DEFERRED;

    DROP SERVER repeaters_fdw CASCADE;
"""

REPEATERS_APP_LABEL = "repeaters"


class RepeatersMigration(migrations.RunSQL):

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if self.should_apply(schema_editor):
            assert count_records(schema_editor.connection, "repeatrecord") == 0
            assert count_records(schema_editor.connection, "repeatrecordattempt") == 0
            self._run_sql(schema_editor, self.sql.format(**self.context))

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if self.should_apply(schema_editor):
            assert count_records(schema_editor.connection, "repeatrecord") == 0
            assert count_records(schema_editor.connection, "repeatrecordattempt") == 0
            self._run_sql(schema_editor, self.reverse_sql.format(**self.context))

    def should_apply(self, schema_editor):
        db_alias = schema_editor.connection.alias
        return db_alias == DEFAULT_DB_ALIAS and repeaters_db() != DEFAULT_DB_ALIAS

    @property
    def context(self):
        db = repeaters_db()
        assert db != DEFAULT_DB_ALIAS
        return settings.DATABASES[db]


def repeaters_db():
    return settings.CUSTOM_DB_ROUTING.get(REPEATERS_APP_LABEL, DEFAULT_DB_ALIAS)


def count_records(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM repeaters_{table}")
        return cursor.fetchone()[0]


class Migration(migrations.Migration):

    dependencies = [
        ('repeaters', '0001_adjust_auth_field_format_squashed_0015_drop_connection_settings_fk'),
    ]

    operations = [
        # Cannot be applied until the repeaters database has been initialized
        # and migrated. The migration should be applied with:
        #
        #   ./manage.py migrate --database=repeaters  # initialize repeaters db
        #   ./manage.py migrate                       # create repeaters FDW
        #
        RepeatersMigration(MOVE_TO_SEPARATE_DB, UNDO_MOVE_TO_SEPARATE_DB),
    ]
