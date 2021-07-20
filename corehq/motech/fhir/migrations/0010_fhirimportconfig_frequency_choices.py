# Generated by Django 2.2.24 on 2021-07-02 23:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fhir', '0009_resourcetyperelationship_related_resource_is_parent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fhirimportconfig',
            name='frequency',
            field=models.CharField(
                choices=[
                    ('daily', 'Daily'),
                    ('weekly', 'Weekly'),
                    ('monthly', 'Monthly')
                ],
                default='daily',
                max_length=12,
            ),
        ),
    ]
