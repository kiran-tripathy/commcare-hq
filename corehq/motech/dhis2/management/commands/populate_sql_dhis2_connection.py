from corehq.apps.cleanup.management.commands.populate_sql_model_from_couch_model import PopulateSQLCommand


class Command(PopulateSQLCommand):
    help = """
        Adds a SQLDhis2Connection for any Dhis2Connection doc that doesn't yet have one.
    """

    @property
    def couch_doc_type(self):
        return 'Dhis2Connection'

    @property
    def couch_key(self):
        return set(['domain'])

    @property
    def sql_class(self):
        from corehq.motech.dhis2.models import SQLDhis2Connection
        return SQLDhis2Connection

    def update_or_create_sql_object(self, doc):
        model, created = self.sql_class.objects.update_or_create(
            domain=doc['domain'],
            defaults={
                'server_url': doc.get('server_url'),
                'username': doc.get('username'),
                'password': doc.get('password'),
                'skip_cert_verify': doc.get('skip_cert_verify') or False,
            }
        )
        return (model, created)
