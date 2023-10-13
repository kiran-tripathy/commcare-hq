# Generated by Django 3.2.20 on 2023-09-20 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geospatial', '0003_auto_20230908_0927'),
    ]

    operations = [
        migrations.AddField(
            model_name='geoconfig',
            name='max_cases_per_group',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='geoconfig',
            name='min_cases_per_group',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='geoconfig',
            name='selected_disbursement_algorithm',
            field=models.CharField(choices=[('radial_algorithm', 'Radial Algorithm'), ('road_network_algorithm', 'Road Network Algorithm')], default='road_network_algorithm', max_length=50),
        ),
        migrations.AddField(
            model_name='geoconfig',
            name='selected_grouping_method',
            field=models.CharField(choices=[('min_max_grouping', 'Min/Max Grouping'), ('target_size_grouping', 'Target Size Grouping')], default='min_max_grouping', max_length=50),
        ),
        migrations.AddField(
            model_name='geoconfig',
            name='target_group_count',
            field=models.IntegerField(null=True),
        ),
    ]
