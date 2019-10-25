from casexml.apps.phone.models import SyncLogSQL
from pillowtop.dao.django import DjangoDocumentStore


class ReadonlySyncLogDocumentStore(DjangoDocumentStore):
    def __init__(self):

        def _to_doc(model):
            return model.doc

        super().__init__(SyncLogSQL, doc_generator_fn=_to_doc)
