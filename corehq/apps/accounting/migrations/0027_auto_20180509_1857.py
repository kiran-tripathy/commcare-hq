# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-09 18:57
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0026_auto_20180508_1956'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='billingrecord',
            name='emailed_to',
        ),
        migrations.RemoveField(
            model_name='wirebillingrecord',
            name='emailed_to',
        ),
    ]
