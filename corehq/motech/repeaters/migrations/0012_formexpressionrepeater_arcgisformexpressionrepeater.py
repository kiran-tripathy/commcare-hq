# Generated by Django 4.2.11 on 2024-07-24 13:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('repeaters', '0011_remove_obsolete_entities'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormExpressionRepeater',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('repeaters.baseexpressionrepeater',),
        ),
        migrations.CreateModel(
            name='ArcGISFormExpressionRepeater',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('repeaters.formexpressionrepeater',),
        ),
    ]
