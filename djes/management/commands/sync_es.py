from django.core.management.base import BaseCommand, CommandError

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



class Command(BaseCommand):
    help = "Creates ES indices, and ensures that mappings are up to date"

    def handle(self, *args, **options):

        indexes = {index_name: {"settings": settings} for (index_name, settings) in settings.ES_INDEX_SETTINGS}
        for model in indexable_registry.all_models:
            if model.mapping.index not in indexes:
                indexes[index] = {}




        print(indexes)

        # for index, settings in indexes.items():
        #     if es.indices.exists(index=index):