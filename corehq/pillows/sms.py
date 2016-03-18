from corehq.apps.change_feed import topics
from corehq.apps.change_feed.consumer.feed import KafkaChangeFeed
from corehq.elastic import get_es_new
from corehq.apps.sms.models import SMSLog
from corehq.pillows.mappings.sms_mapping import SMS_MAPPING, SMS_INDEX
from dimagi.utils.decorators.memoized import memoized
from pillowtop.checkpoints.manager import PillowCheckpoint, PillowCheckpointEventHandler
from pillowtop.es_utils import ElasticsearchIndexMeta
from pillowtop.listener import AliasedElasticPillow
from pillowtop.pillow.interface import ConstructedPillow
from pillowtop.processors.elastic import ElasticProcessor
from django.conf import settings

SMS_PILLOW_CHECKPOINT_ID = 'sql-sms-to-es'
SMS_PILLOW_KAFKA_CONSUMER_GROUP_ID = 'sql-sms-to-es'

ES_SMS_INDEX = SMS_INDEX
ES_SMS_TYPE = 'sms'


class SMSPillow(AliasedElasticPillow):
    """
    Simple/Common Case properties Indexer
    """

    document_class = SMSLog   # while this index includes all users,
                                    # I assume we don't care about querying on properties specfic to WebUsers
    couch_filter = "sms/all_logs"
    es_timeout = 60
    es_alias = "smslogs"
    es_type = ES_SMS_TYPE
    es_meta = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "custom",
                        "tokenizer": "whitespace",
                        "filter": ["lowercase"]
                    },
                }
            }
        }
    }
    es_index = ES_SMS_INDEX
    default_mapping = SMS_MAPPING

    @classmethod
    @memoized
    def calc_meta(cls):
        #todo: actually do this correctly

        """
        override of the meta calculator since we're separating out all the types,
        so we just do a hash of the "prototype" instead to determined md5
        """
        return cls.calc_mapping_hash({"es_meta": cls.es_meta, "mapping": cls.default_mapping})


def get_sql_sms_pillow(pillow_id):
    checkpoint = PillowCheckpoint(SMS_PILLOW_CHECKPOINT_ID)
    processor = ElasticProcessor(
        elasticseach=get_es_new(),
        index_meta=ElasticsearchIndexMeta(index=ES_SMS_INDEX, type=ES_SMS_TYPE),
        doc_prep_fn=lambda x: x
    )
    return ConstructedPillow(
        name=pillow_id,
        document_store=None,
        checkpoint=checkpoint,
        change_feed=KafkaChangeFeed(topics=[topics.SMS], group_id=SMS_PILLOW_KAFKA_CONSUMER_GROUP_ID),
        processor=processor,
        change_processed_event_handler=PillowCheckpointEventHandler(
            checkpoint=checkpoint, checkpoint_frequency=100,
        ),
    )
