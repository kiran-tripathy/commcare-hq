# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2019-12-12 09:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SQLAppGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_id', models.CharField(max_length=255)),
                ('group_id', models.CharField(max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SQLApplicationAccess',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=255, unique=True)),
                ('restrict', models.BooleanField(default=False)),
            ],
        ),
        migrations.AddField(
            model_name='sqlappgroup',
            name='application_access',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    to='cloudcare.SQLApplicationAccess'),
        ),
        migrations.AlterUniqueTogether(
            name='sqlappgroup',
            unique_together=set([('app_id', 'group_id')]),
        ),
    ]
