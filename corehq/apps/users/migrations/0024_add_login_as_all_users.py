from django.db import migrations

from corehq.util.django_migrations import prompt_for_historical_migration, get_migration_name


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_hqapikey_role_id'),
    ]

    operations = {
        prompt_for_historical_migration(
            "users", get_migration_name(__file__), "a7c40ca6acf609b22b495ab986c11f3524b47ce7")
    }
