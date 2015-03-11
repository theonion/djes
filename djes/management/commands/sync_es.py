from django.core.management.base import BaseCommand, CommandError
from elasticsearch import TransportError
from elasticsearch_dsl.connections import connections

from djes.apps import indexable_registry
from djes.conf import settings


def get_indexes():
    indexes = {}
    for index, models in indexable_registry.indexes.items():
        indexes[index] = {
            "mappings": {}
        }

        if index in settings.ES_INDEX_SETTINGS:
            indexes[index]["settings"] = settings.ES_INDEX_SETTINGS[index]

        for model in models:
            indexes[index]["mappings"].update(model.mapping.to_dict())

    return indexes


def build_versioned_index(name, version=1, body=None, old_version=None):
    es = connections.get_connection("default")
    versioned_index_name = "{0}_{1:0>4}".format(name, version)
    es.indices.create(index=versioned_index_name, body=body)

    # TODO: bulk index in here...

    actions = [{"add": {"index": versioned_index_name, "alias": name}}]
    if old_version is not None:
        old_versioned_index_name = "{0}_{1:0>4}".format(name, old_version)
        actions.insert(0, {"remove": {"index": old_versioned_index_name, "alias": name}})

    es.indices.update_aliases(body={"actions": actions})


def sync_index(name, body):
    es = connections.get_connection("default")

    if not es.indices.exists_alias(name=name):
        # We probably haven't synced before, that means we need to create an index, and then alias it
        build_versioned_index(name, body=body)
        return

    # The alias exists, so there's already a version of this index out there
    alias = es.indices.get_alias(name=name)

    # There will only be one key, let's the name from it
    versioned_index_name = alias.keys()[0]
    if "settings" in body:
        settings = es.indices.get_settings(index=versioned_index_name)[versioned_index_name]["settings"]

        # This is a little hard to understand, but it works (credit: http://stackoverflow.com/q/9323749/931098)
        if not all(item in settings.items() for item in body["settings"].items()):
            # We need to update the settings...
            es.indices.put_settings(index=versioned_index_name, body=body["settings"])

    server_mappings = es.indices.get_mapping(index=versioned_index_name)[versioned_index_name]["mappings"]

    for doc_type, mapping_body in body["mappings"].items():
        if mapping_body != server_mappings.get(doc_type, {}):
            try:
                es.indices.put_mapping(index=versioned_index_name, doc_type=doc_type, body=mapping_body)
            except TransportError as e:
                if "MergeMappingException" in e.error:
                    # We need to do this the hard way
                    old_version = int(versioned_index_name.split("_")[-1])
                    new_version = old_version + 1
                    build_versioned_index(name, version=new_version, body=body, old_version=old_version)
                    break
                else:
                    raise e


class Command(BaseCommand):
    help = "Creates ES indices, and ensures that mappings are up to date"

    def handle(self, *args, **options):

        indexes = get_indexes()

        for index, body in indexes.items():
            sync_index(index, body)
