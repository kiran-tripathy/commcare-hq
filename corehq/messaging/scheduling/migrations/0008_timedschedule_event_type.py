# Generated by Django 1.11.7 on 2017-12-12 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0007_add_schedule_ui_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='timedschedule',
            name='event_type',
            field=models.CharField(default='SPECIFIC_TIME', max_length=50),
        ),
    ]
