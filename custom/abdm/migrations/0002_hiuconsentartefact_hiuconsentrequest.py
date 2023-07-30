# Generated by Django 3.2.19 on 2023-07-27 15:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('abdm', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HIUConsentRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gateway_request_id', models.UUIDField(null=True, unique=True)),
                ('consent_request_id', models.UUIDField(null=True, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending request from Gateway'), ('REQUESTED', 'Requested'), ('GRANTED', 'Granted'), ('DENIED', 'Denied'), ('REVOKED', 'Revoked'), ('EXPIRED', 'Expired'), ('ERROR', 'Error occurred')], default='PENDING', max_length=40)),
                ('details', models.JSONField(null=True)),
                ('error', models.JSONField(null=True)),
                ('health_info_from_date', models.DateTimeField()),
                ('health_info_to_date', models.DateTimeField()),
                ('health_info_types', models.JSONField(default=list)),
                ('expiry_date', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consent_requests', to='abdm.abdmuser')),
            ],
        ),
        migrations.CreateModel(
            name='HIUConsentArtefact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gateway_request_id', models.UUIDField(null=True, unique=True)),
                ('artefact_id', models.UUIDField(unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('GRANTED', 'Granted'), ('REVOKED', 'Revoked'), ('EXPIRED', 'Expired'), ('ERROR', 'Error occurred')], max_length=40)),
                ('details', models.JSONField(null=True)),
                ('error', models.JSONField(null=True)),
                ('consent_request', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='artefacts', to='abdm.hiuconsentrequest', to_field='consent_request_id')),
            ],
        ),
    ]
