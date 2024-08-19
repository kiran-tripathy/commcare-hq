# Generated by Django 4.2.14 on 2024-07-26 10:39

from django.db import migrations


def remove_unicel_backend(apps, schema_editor):
    SQLMobileBackend = apps.get_model('sms', 'SQLMobileBackend')
    unicel_backends = SQLMobileBackend.objects.filter(hq_api_id='UNICEL')
    unicel_backends.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sms', '0058_email_html_body'),
    ]

    operations = [
        migrations.RunPython(remove_unicel_backend, reverse_code=migrations.RunPython.noop)
    ]
