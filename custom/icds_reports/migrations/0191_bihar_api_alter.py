# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2020-05-13 09:54
from __future__ import unicode_literals

from django.db import migrations, models

from corehq.sql_db.operations import RawSQLMigration
from custom.icds_reports.utils.migrations import get_view_migrations

migrator = RawSQLMigration(('custom', 'icds_reports', 'migrations', 'sql_templates'))


class Migration(migrations.Migration):
    dependencies = [
        ('icds_reports', '0190_added_was_oos_ever'),
    ]

    operations = [
        migrations.AddField(
            model_name='biharapidemographics',
            name='last_reported_fever_date',
            field=models.DateField(null=True)
        ),
        migrations.RunSQL(
            "ALTER table icds_dashboard_ccs_record_bp_forms ADD COLUMN new_ifa_tablets_total SMALLINT"),
        migrations.RunSQL(
            "ALTER table icds_dashboard_ccs_record_bp_forms ADD COLUMN reason_no_ifa TEXT"),
        migrations.RunSQL(
            "ALTER table icds_dashboard_ccs_record_postnatal_forms ADD COLUMN new_ifa_tablets_total SMALLINT"),
        migrations.RunSQL("ALTER TABLE ccs_record_monthly ADD COLUMN complication_type TEXT"),
        migrations.RunSQL("ALTER TABLE ccs_record_monthly ADD COLUMN reason_no_ifa TEXT"),
        migrations.RunSQL("ALTER TABLE ccs_record_monthly ADD COLUMN new_ifa_tablets_total_bp INTEGER"),
        migrations.RunSQL("ALTER TABLE ccs_record_monthly ADD COLUMN new_ifa_tablets_total_pnc INTEGER"),
        migrations.RunSQL("ALTER TABLE ccs_record_monthly ADD COLUMN ifa_last_seven_days INTEGER"),
    ]

    operations.extend(get_view_migrations())
