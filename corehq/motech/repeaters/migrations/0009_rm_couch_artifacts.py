# Generated by Django 3.2.23 on 2024-01-16 20:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('repeaters', '0008_sqlrepeatrecords'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(
                    model_name='sqlrepeatrecord',
                    name='unique_couch_id',
                ),
                migrations.RemoveField(
                    model_name='sqlrepeatrecord',
                    name='couch_id',
                ),
                # state-only to prevent drop/create attempts foreign key
                migrations.RenameModel(
                    old_name='SQLRepeatRecord',
                    new_name='RepeatRecord',
                ),
                migrations.AlterModelTable(
                    name='repeatrecord',
                    table=None,
                ),
                migrations.RenameModel(
                    old_name='SQLRepeatRecordAttempt',
                    new_name='RepeatRecordAttempt',
                ),
                migrations.AlterModelTable(
                    name='repeatrecordattempt',
                    table=None,
                ),
            ],
        ),
    ]


# SQL operations to be done later
#
# DROP INDEX IF EXISTS "unique_couch_id";
# ALTER TABLE "repeaters_repeatrecord" DROP COLUMN "couch_id" CASCADE;
