# Generated by Django 3.2.20 on 2023-09-22 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('abdm', '0005_hipcarecontext_hiplinkrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='hipcarecontext',
            name='health_info_types',
            field=models.JSONField(default=list),
        ),
    ]
