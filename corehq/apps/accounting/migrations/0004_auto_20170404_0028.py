# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-04 00:28
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations

from corehq.apps.hqadmin.management.commands.cchq_prbac_bootstrap import cchq_prbac_bootstrap
from corehq.sql_db.operations import HqRunPython


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0003_auto_20170328_2102'),
    ]

    operations = [
        HqRunPython(cchq_prbac_bootstrap),
    ]
