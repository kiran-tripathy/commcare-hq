# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-04 12:13
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0080_merge_20181130_1818'),
    ]

    operations = [
        migrations.RenameField(
            model_name='aggls',
            old_name='unique_awc_vists',
            new_name='awc_visits'
        ),
        migrations.RenameField(
            model_name='aggregatelsawcvisitform',
            old_name='unique_awc_vists',
            new_name='awc_visits'
        )
    ]
