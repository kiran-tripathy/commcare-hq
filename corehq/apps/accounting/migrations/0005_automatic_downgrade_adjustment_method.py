# Generated by Django 1.10.7 on 2017-04-14 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_auto_20170404_0028'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptionadjustment',
            name='method',
            field=models.CharField(choices=[('USER', 'User'), ('INTERNAL', 'Ops'), ('TASK', 'Task (Invoicing)'), ('TRIAL', '30 Day Trial'), ('AUTOMATIC_DOWNGRADE', 'Automatic Downgrade')], default='INTERNAL', max_length=50),
        ),
    ]
