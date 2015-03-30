from django.apps import AppConfig, apps

from .mapping import DjangoMapping
from .conf import settings

from elasticsearch_dsl.connections import connections


class IndexableRegistry(object):
    """Contains information about all PolymorphicIndexables in the project."""
    def __init__(self):
        self.all_models = {}
        self.families = {}
        self.indexes = {}

    def register(self, klass):
        """Adds a new PolymorphicIndexable to the registry."""

        # Get the mapping class for this model
        if hasattr(klass, "Mapping"):
            # TODO: Inherit all parent mapping info
            mapping_klass = type("Mapping", (DjangoMapping, klass.Mapping), {})
        else:
            mapping_klass = DjangoMapping

        # Cache the mapping instance on the model
        klass.mapping = mapping_klass(klass)

        # Now we can get the doc_type
        doc_type = klass.mapping.doc_type

        self.all_models[doc_type] = klass
        base_class = klass.get_base_class()
        if base_class not in self.families:
            self.families[base_class] = {}
        self.families[base_class][doc_type] = klass

        if klass.mapping.index not in self.indexes:
            self.indexes[klass.mapping.index] = []

        self.indexes[klass.mapping.index].append(klass)


indexable_registry = IndexableRegistry()


class DJESConfig(AppConfig):
    name = 'djes'
    verbose_name = "DJ E.S."

    def ready(self):

        # Let's register all the Indexable models
        for model in apps.get_models():

            # If it quacks...
            if hasattr(model, "from_es"):
                meta = getattr(model, "_meta")
                if meta and not getattr(meta, "abstract"):
                    indexable_registry.register(model)

    connections.configure(**settings.ES_CONNECTIONS)
