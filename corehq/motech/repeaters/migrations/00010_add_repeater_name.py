# Generated by Django 3.2.16 on 2022-11-18 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repeaters', '0009_add_create_update_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='sqlrepeater',
            name='name',
            field=models.CharField(max_length=64, null=True),
        ),
    ]
