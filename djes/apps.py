from django.apps import AppConfig, apps

from .mapping import DjangoMapping
from .conf import settings

from elasticsearch_dsl.connections import connections


def get_first_mapping(cls):
    """This allows for Django-like inheritance of mapping configurations"""

    if hasattr(cls, "from_es") and hasattr(cls, "Mapping"):
        return cls.Mapping
    for base in cls.__bases__:
        mapping = get_first_mapping(base)
        if mapping:
            return mapping
    return None


class IndexableRegistry(object):
    """Contains information about all PolymorphicIndexables in the project."""
    def __init__(self):
        self.all_models = {}
        self.families = {}
        self.indexes = {}

    def register(self, cls):
        """Adds a new PolymorphicIndexable to the registry."""

        # Get the mapping class for this model
        if hasattr(cls, "Mapping"):
            mapping_klass = type("Mapping", (DjangoMapping, cls.Mapping), {})
        else:
            mapping_klass = get_first_mapping(cls)
            if mapping_klass is None:
                mapping_klass = DjangoMapping

        # Cache the mapping instance on the model
        cls.mapping = mapping_klass(cls)

        # Now we can get the doc_type
        doc_type = cls.mapping.doc_type

        self.all_models[doc_type] = cls
        base_class = cls.get_base_class()
        if base_class not in self.families:
            self.families[base_class] = {}
        self.families[base_class][doc_type] = cls

        if cls.mapping.index not in self.indexes:
            self.indexes[cls.mapping.index] = []

        self.indexes[cls.mapping.index].append(cls)


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
