# Generated by Django 2.2.20 on 2021-04-29 21:40

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0025_hqapikey_domain'),
        ('registration', '0004_rename_sqlregistrationrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='AsyncSignupRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=255)),
                ('phone_number', models.CharField(blank=True, max_length=126, null=True)),
                ('project_name', models.CharField(blank=True, max_length=255, null=True)),
                ('atypical_user', models.BooleanField(default=False)),
                ('persona', models.CharField(blank=True, max_length=128, null=True)),
                ('persona_other', models.TextField(blank=True, null=True)),
                ('additional_hubspot_data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('invitation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.Invitation')),
            ],
        ),
    ]
