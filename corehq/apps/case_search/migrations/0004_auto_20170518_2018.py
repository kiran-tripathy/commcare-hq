# Generated by Django 1.10.7 on 2017-05-18 20:18

import django.contrib.postgres.fields
from django.db import migrations, models

import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('case_search', '0003_casesearchqueryaddition'),
    ]

    operations = [
        migrations.CreateModel(
            name='FuzzyProperties',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(db_index=True, max_length=256)),
                ('case_type', models.CharField(db_index=True, max_length=256)),
                ('properties', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(blank=True, null=True), null=True, size=None)),
            ],
        ),
        migrations.AlterField(
            model_name='casesearchqueryaddition',
            name='query_addition',
            field=jsonfield.fields.JSONField(default=dict, help_text="More information about how this field is used can be found <a href='https://docs.google.com/document/d/1MKllkHZ6JlxhfqZLZKWAnfmlA3oUqCLOc7iKzxFTzdY/edit#heading=h.k5pky76mwwon'>here</a>. This ES <a href='https://www.elastic.co/guide/en/elasticsearch/guide/1.x/bool-query.html'>documentation</a> may also be useful. This JSON will be merged at the `query.filtered.query` path of the query JSON."),
        ),
        migrations.AlterUniqueTogether(
            name='fuzzyproperties',
            unique_together=set([('domain', 'case_type')]),
        ),
        migrations.AddField(
            model_name='casesearchconfig',
            name='fuzzy_properties',
            field=models.ManyToManyField(to='case_search.FuzzyProperties'),
        ),
    ]
