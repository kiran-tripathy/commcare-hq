# Generated by Django 3.2.20 on 2023-09-12 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ABDMUser',
            fields=[
                ('username', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('access_token', models.CharField(blank=True, max_length=2000, null=True)),
                ('domain', models.CharField(default='', max_length=100)),
            ],
        ),
    ]
