# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-03-30 04:51
from __future__ import unicode_literals
from __future__ import absolute_import

from datetime import datetime

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0026_real_foreign_keys_and_no_sync_build'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationstatusfact',
            name='domain',
            field=models.CharField(db_index=True, default=0, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicationstatusfact',
            name='last_form_app_build_version',
            field=models.CharField(default=0, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicationstatusfact',
            name='last_form_app_commcare_version',
            field=models.CharField(default=0, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicationstatusfact',
            name='last_form_submission_date',
            field=models.DateTimeField(default=datetime(1900, 1, 1)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicationstatusfact',
            name='last_sync_log_date',
            field=models.DateTimeField(default=datetime(1900, 1, 1)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='synclogfact',
            name='domain_dim',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='warehouse.DomainDim'),
        ),
    ]
