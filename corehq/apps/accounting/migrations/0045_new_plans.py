# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-09-13 22:26
from __future__ import unicode_literals

from django.db import migrations
from django.core.management import call_command

from corehq.util.django_migrations import skip_on_fresh_install
from corehq.privileges import PROJECT_ACCESS
from corehq.apps.accounting.bootstrap.utils import ensure_plans
from corehq.apps.accounting.bootstrap.config.new_plans_dec_2019 import \
    BOOTSTRAP_CONFIG as new_plans_config


@skip_on_fresh_install
def _grandfather_basic_privs(apps, schema_editor):
    call_command('cchq_prbac_bootstrap')
    call_command(
        'cchq_prbac_grandfather_privs',
        PROJECT_ACCESS,
        skip_edition='Paused',
        noinput=True,
    )


def _ensure_new_software_plans(apps, schema_editor):
    ensure_plans(new_plans_config, verbose=True, apps=apps)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0044_grandfather_odata_privs'),
    ]

    operations = [
        migrations.RunPython(_grandfather_basic_privs),
        migrations.RunPython(_ensure_new_software_plans),
    ]
