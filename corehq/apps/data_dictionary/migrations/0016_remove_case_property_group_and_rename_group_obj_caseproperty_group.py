# Generated by Django 3.2.20 on 2023-10-25 10:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_dictionary', '0015_casetype_is_deprecated'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='caseproperty',
            name='group',
        ),
        migrations.RenameField(
            model_name='caseproperty',
            old_name='group_obj',
            new_name='group',
        ),
    ]
