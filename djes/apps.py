from django.apps import AppConfig, apps

from .conf import settings

from elasticsearch_dsl.connections import connections


class IndexableRegistry(object):
    """Contains information about all PolymorphicIndexables in the project."""
    def __init__(self):
        self.all_models = {}
        self.families = {}
        self.indexes = {}

    def register(self, cls):
        """Adds a new PolymorphicIndexable to the registry."""
        doc_type = cls.search_objects.mapping.doc_type

        self.all_models[doc_type] = cls
        base_class = cls.get_base_class()
        if base_class not in self.families:
            self.families[base_class] = {}
        self.families[base_class][doc_type] = cls

        if cls.search_objects.mapping.index not in self.indexes:
            self.indexes[cls.search_objects.mapping.index] = []

        self.indexes[cls.search_objects.mapping.index].append(cls)


indexable_registry = IndexableRegistry()


class DJESConfig(AppConfig):
    name = 'djes'
    verbose_name = "DJ E.S."

    def ready(self):
        from .models import Indexable

        # Let's register all the Indexable models
        for model in apps.get_models():

            # If it quacks...
            if issubclass(model, Indexable):
                meta = getattr(model, "_meta")
                if meta and not getattr(meta, "abstract"):
                    indexable_registry.register(model)

    connections.configure(**settings.ES_CONNECTIONS)
