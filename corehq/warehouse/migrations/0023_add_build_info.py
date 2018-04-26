# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-01-31 10:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0022_userstagingtable_assigned_location_ids'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationdim',
            name='copy_of',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='applicationdim',
            name='version',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='applicationstagingtable',
            name='copy_of',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='applicationstagingtable',
            name='version',
            field=models.IntegerField(null=True),
        ),
    ]
