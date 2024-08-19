# Generated by Django 4.2.11 on 2024-07-04 17:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0095_update_softwareplan_visibilities'),
    ]

    operations = [
        migrations.AlterField(
            model_name='creditline',
            name='feature_type',
            field=models.CharField(blank=True, choices=[('User', 'User'), ('SMS', 'SMS'), ('Web User', 'Web User'), (
                'Form-Submitting Mobile Worker', 'Form-Submitting Mobile Worker')], max_length=40, null=True),
        ),
        migrations.AlterField(
            model_name='feature',
            name='feature_type',
            field=models.CharField(choices=[('User', 'User'), ('SMS', 'SMS'), ('Web User', 'Web User'),
                                   ('Form-Submitting Mobile Worker', 'Form-Submitting Mobile Worker')], db_index=True, max_length=40),
        ),
        migrations.CreateModel(
            name='FormSubmittingMobileWorkerHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=256)),
                ('record_date', models.DateField()),
                ('num_users', models.IntegerField(default=0)),
            ],
            options={
                'abstract': False,
                'unique_together': {('domain', 'record_date')},
            },
        ),
    ]
