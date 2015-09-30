from django.core.management.base import BaseCommand
from elasticsearch_dsl.connections import connections
from elasticsearch.helpers import streaming_bulk

from djes.apps import indexable_registry
from djes.conf import settings
from djes.util import batched_queryset


def model_iterator(model, index=None, out=None):
    if index is None:
        index = model.search_objects.mapping.index

    counter = 0
    total = model.search_objects.count()
    if out:
        out.write("Indexing {} {} objects".format(total, model.__name__))
    for obj in batched_queryset(model.objects.all()):
        if obj.__class__ != model:
            # TODO: Come up with a better method to avoid redundant indexing
            continue
        counter += 1
        if counter % 100 == 0:
            if out:
                out.write("Indexed {}/{} {} objects".format(counter, total, model.__name__))
        yield {
            "_id": obj.pk,
            "_index": index,
            "_type": obj.mapping.doc_type,
            "_source": obj.to_dict()
        }


def bulk_index(es, index=None, version=1, out=None):
    if index not in indexable_registry.indexes:
        # Looks like someone is requesting the indexing of something we don't have models for
        return

    vindex = "{0}_{1:0>4}".format(index, version)

    es.indices.put_settings(
        index=vindex,
        body={"index": {"refresh_interval": "-1"}}
    )

    for model in indexable_registry.indexes[index]:

        identifier = "{}.{}".format(model._meta.app_label, model._meta.object_name)
        if identifier in settings.DJES_EXCLUDED_MODELS:
            continue

        for ok, res in streaming_bulk(es, model_iterator(model, index=vindex, out=out)):
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

            bulk_index(es, index=index, version=version, out=self.stdout)
