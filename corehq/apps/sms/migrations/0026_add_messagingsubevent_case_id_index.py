# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-10-13 10:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sms', '0025_add_custom_metadata'),
    ]

    operations = [
        migrations.CreateModel(
            name='StartEnterpriseBackend',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('sms.sqlsmsbackend',),
        ),
        migrations.AlterField(
            model_name='messagingsubevent',
            name='case_id',
            field=models.CharField(db_index=True, max_length=126, null=True),
        ),
    ]
