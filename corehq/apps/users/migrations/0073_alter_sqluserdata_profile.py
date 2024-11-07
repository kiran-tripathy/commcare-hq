# Generated by Django 4.2.16 on 2024-11-07 15:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("custom_data_fields", "0009_field_required_for"),
        ("users", "0072_remove_invitation_supply_point"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sqluserdata",
            name="profile",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="custom_data_fields.customdatafieldsprofile",
            ),
        ),
    ]
