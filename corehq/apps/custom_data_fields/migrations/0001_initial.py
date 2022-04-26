# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2020-04-27 00:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SQLCustomDataFieldsDefinition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_type', models.CharField(max_length=126)),
                ('domain', models.CharField(max_length=255, null=True)),
                ('couch_id', models.CharField(db_index=True, max_length=126, null=True)),
            ],
            options={
                'db_table': 'custom_data_fields_customdatafieldsdefinition',
            },
        ),
        migrations.CreateModel(
            name='SQLField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.CharField(max_length=127)),
                ('is_required', models.BooleanField(default=False)),
                ('label', models.CharField(max_length=255)),
                ('choices', models.JSONField(default=list, null=True)),
                ('regex', models.CharField(max_length=127, null=True)),
                ('regex_msg', models.CharField(max_length=255, null=True)),
                ('definition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 to='custom_data_fields.SQLCustomDataFieldsDefinition')),
            ],
            options={
                'db_table': 'custom_data_fields_field',
            },
        ),
        migrations.AlterUniqueTogether(
            name='sqlcustomdatafieldsdefinition',
            unique_together=set([('domain', 'field_type')]),
        ),
        migrations.AlterOrderWithRespectTo(
            name='sqlfield',
            order_with_respect_to='definition',
        ),
    ]
