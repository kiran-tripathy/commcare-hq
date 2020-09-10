# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-06-26 14:25
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('custom_data_fields', '0004_rename_tables'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomDataFieldsProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=126)),
                ('fields', django.contrib.postgres.fields.jsonb.JSONField(default=list, null=True)),
                ('definition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 to='custom_data_fields.CustomDataFieldsDefinition')),
            ],
        ),
    ]
