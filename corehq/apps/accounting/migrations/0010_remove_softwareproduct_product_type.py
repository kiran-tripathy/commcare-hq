# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-22 18:42
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0009_make_billingaccount_name_unique'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='softwareproduct',
            name='product_type',
        ),
    ]
