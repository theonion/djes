from django.core.management.base import BaseCommand
from elasticsearch_dsl.connections import connections
from elasticsearch.helpers import streaming_bulk

from djes.apps import indexable_registry


def model_iterator(model):
    for obj in model.search_objects.iterator():
        yield obj.to_dict()


def bulk_index(es, index=None, version=1):

    if index not in indexable_registry.indexes:
        # Looks like someone is requesting the indexing of something we don't have models for
        return

    vindex = "{0}_{1:0>4}".format(index, version)

    es.indices.put_settings(
        index=vindex,
        body={"index": {"refresh_interval": "-1"}}
    )

    for model in indexable_registry.indexes[index]:
        doc_type = model.search_objects.mapping.doc_type
        for ok, res in streaming_bulk(es, model_iterator(model), index=vindex, doc_type=doc_type):
            continue

    es.indices.put_settings(
        index=vindex,
        body={"index": {"refresh_interval": "1"}}
    )


class Command(BaseCommand):
    help = "Creates ES indices, and ensures that mappings are up to date"

    def handle(self, *args, **options):

        es = connections.get_connection("default")
        for index in list(indexable_registry.indexes):

            alias = es.indices.get_alias(index)
            index_name = list(alias)[0]
            version = int(index_name.split("_")[-1])

            bulk_index(es, index=index, version=version)
