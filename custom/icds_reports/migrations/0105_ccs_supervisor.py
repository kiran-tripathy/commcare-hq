# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.apps import apps
from django.conf import settings
from django.db import migrations

from corehq.sql_db.operations import SQL


def _citus_composite_key_sql(model_cls):
    pkey_name = '{}_pkey'.format(model_cls._meta.db_table)
    fields = list(model_cls._meta.unique_together)[0]
    columns = [model_cls._meta.get_field(field).column for field in fields]
    index = '{}_{}_uniq'.format(model_cls._meta.db_table, '_'.join(columns))
    sql = SQL("""
        CREATE UNIQUE INDEX {index} on "{table}" ({cols});
        ALTER TABLE "{table}" ADD CONSTRAINT {pkey_name} PRIMARY KEY USING INDEX {index};
    """.format(
        table=model_cls._meta.db_table,
        pkey_name=pkey_name,
        index=index,
        cols=','.join(columns)
    ))
    reverse_sql = SQL("""
        ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS {index},
        DROP CONSTRAINT IF EXISTS {pkey_name},
        ADD CONSTRAINT {pkey_name} PRIMARY KEY ({pkey});
        DROP INDEX IF EXISTS {index};
    """.format(
        table=model_cls._meta.db_table,
        pkey_name=pkey_name,
        pkey=model_cls._meta.pk.name,
        index=index,
    ))
    if getattr(settings, 'UNIT_TESTING', False):
        return sql, reverse_sql
    else:
        return migrations.RunSQL.noop, reverse_sql


def get_sql_operations():
    models_to_update = [
        'ccsrecordmonthly',
        'childhealthmonthly'
    ]

    operations = []
    for model_name in models_to_update:
        model = apps.get_model('icds_reports', model_name)
        sql, reverse_sql = _citus_composite_key_sql(model)
        operations.append(migrations.RunSQL(
            sql,
            reverse_sql,
        ))
    return operations


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0104_citus_composite_key'),
    ]

    operations = [
        migrations.RunSQL("""
        ALTER TABLE ccs_record_monthly ADD COLUMN supervisor_id text;
        ALTER TABLE child_health_monthly ADD COLUMN supervisor_id text;
        """)
    ]
    operations.extend(get_sql_operations())
