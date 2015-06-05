from django.core.management.base import BaseCommand
from django.utils.encoding import smart_text
from elasticsearch import TransportError
from elasticsearch_dsl.connections import connections

from djes.apps import indexable_registry
from djes.conf import settings
from djes.management.commands.bulk_index import bulk_index

import copy


def get_indexes():
    indexes = {}
    for index, models in indexable_registry.indexes.items():
        indexes[index] = {
            "mappings": {}
        }

        if index in settings.ES_INDEX_SETTINGS:
            indexes[index]["settings"] = settings.ES_INDEX_SETTINGS[index]

        for model in models:
            indexes[index]["mappings"].update(model.search_objects.mapping.to_dict())

    return indexes


def build_versioned_index(name, version=1, body=None, old_version=None, should_index=False):
    es = connections.get_connection("default")
    versioned_index_name = "{0}_{1:0>4}".format(name, version)
    es.indices.create(index=versioned_index_name, body=body)

    if should_index:
        bulk_index(es, index=name, version=version)  # Bulk index here...

    actions = [{"add": {"index": versioned_index_name, "alias": name}}]
    if old_version is not None:
        old_versioned_index_name = "{0}_{1:0>4}".format(name, old_version)
        actions.insert(0, {"remove": {"index": old_versioned_index_name, "alias": name}})

    es.indices.update_aliases(body={"actions": actions})


def stringify(data):
    """Turns all dictionary values into strings"""
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = stringify(value)
    elif isinstance(data, list):
        return [stringify(item) for item in data]
    else:
        return smart_text(data)

    return data


def sync_index(name, body, should_index=False):
    es = connections.get_connection("default")

    if not es.indices.exists_alias(name=name):
        # We probably haven't synced before, that means we need to create an index, and then alias
        build_versioned_index(name, body=body, should_index=should_index)
        return

    # The alias exists, so there's already a version of this index out there
    alias = es.indices.get_alias(name=name)

    # There will only be one key, let's the name from it
    index_name = list(alias)[0]
    if "settings" in body:
        settings = es.indices.get_settings(index=index_name)[index_name]["settings"]

        # Let's take a snapshot of the settings for comparison
        original_settings = copy.copy(settings["index"])

        # Let's save off the analysis bits, as those are more complex...
        original_analysis = {}
        if "analysis" in original_settings:
            original_analysis = original_settings.pop("analysis")

        original_settings.update(body["settings"]["index"])

        # We want to make sure that all values are strings, in order for easier comparison
        original_settings = stringify(original_settings)

        # If the index settings have changed, we'll need to PUT an update
        if original_settings != stringify(settings["index"]):
            index_body = copy.copy(body["settings"]["index"])
            if "analysis" in index_body:
                del index_body["analysis"]

            es.indices.put_settings(index=index_name, body=dict(index=index_body))

        # However, if the analyzers have changed, we'll need to close and reopen...
        if "analysis" in body["settings"]["index"]:
            original_analysis.update(body["settings"]["index"]["analysis"])

            # We want to make sure that all values are strings, in order for easier comparison
            original_analysis = stringify(original_analysis)

            if original_analysis != stringify(settings["index"].get("analysis", {})):

                # We need to close the index before we update analyzers
                es.indices.close(index=index_name)

                es.indices.put_settings(index=index_name, body=dict(analysis=body["settings"]["analysis"]))

                # Now we re-open
                es.indices.open(index=index_name)

    server_mappings = es.indices.get_mapping(index=index_name)[index_name]["mappings"]

    for doc_type, mapping_body in body["mappings"].items():
        if mapping_body != server_mappings.get(doc_type, {}):
            try:
                es.indices.put_mapping(index=index_name, doc_type=doc_type, body=mapping_body)
            except TransportError as e:
                if "MergeMappingException" in e.error:
                    # We need to do this the hard way
                    old_version = int(index_name.split("_")[-1])
                    new_version = old_version + 1

                    build_versioned_index(
                        name,
                        version=new_version,
                        body=body,
                        old_version=old_version
                    )
                    break
                else:
                    raise e


class Command(BaseCommand):
    help = "Creates ES indices, and ensures that mappings are up to date"

    def handle(self, *args, **options):

        indexes = get_indexes()

        for index, body in indexes.items():
            sync_index(index, body, should_index=True)
