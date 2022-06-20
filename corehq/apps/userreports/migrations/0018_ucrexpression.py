# Generated by Django 3.2.12 on 2022-04-12 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userreports', '0017_index_cleanup'),
    ]

    operations = [
        migrations.CreateModel(
            name='UCRExpression',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('domain', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('expression_type', models.CharField(choices=[('named_expression', 'named_expression'), ('named_filter', 'named_filter')], db_index=True, default='named_expression', max_length=20)),
                ('definition', models.JSONField(null=True)),
            ],
            options={
                'unique_together': {('name', 'domain')},
            },
        ),
    ]
