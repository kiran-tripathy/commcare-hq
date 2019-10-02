# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-09-30 09:13
from __future__ import unicode_literals

from django.db import migrations, models

from corehq.sql_db.operations import RawSQLMigration

migrator = RawSQLMigration(('custom', 'icds_reports', 'migrations', 'sql_templates'))


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0134_add_infra_field'),
    ]

    operations = [

        migrator.get_migration('update_tables50.sql'),
    ]
