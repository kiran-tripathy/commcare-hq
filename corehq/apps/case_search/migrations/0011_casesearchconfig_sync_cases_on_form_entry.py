# Generated by Django 3.2.17 on 2023-02-14 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('case_search', '0010_casesearchconfig_synchronous_web_apps'),
    ]

    operations = [
        migrations.AddField(
            model_name='casesearchconfig',
            name='sync_cases_on_form_entry',
            field=models.BooleanField(default=False),
        ),
    ]
