# Generated by Django 3.2.15 on 2022-09-14 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ABDMUser',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=100)),
                ('access_token', models.CharField(blank=True, max_length=2000, null=True)),
            ],
        ),
    ]
