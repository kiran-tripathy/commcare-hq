# Generated by Django 3.2.16 on 2023-02-14 06:34

from django.db import migrations
from django.core.management import call_command
from corehq.util.django_migrations import skip_on_fresh_install


@skip_on_fresh_install
def _run_prbac_bootstrap(apps, schema_editor):
    call_command('cchq_prbac_bootstrap')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0050_add_manage_attendance_tracking_permission'),
    ]

    operations = [
        migrations.RunPython(_run_prbac_bootstrap, migrations.RunPython.noop)
    ]
