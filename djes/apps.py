from django.apps import AppConfig

from .models import Indexable
from .conf import settings

from elasticsearch_dsl.connections import connections


def get_base_class(cls):
    while cls.__bases__ and cls.__bases__[0] != Indexable:
        cls = cls.__bases__[0]
    return cls


class IndexableRegistry(object):
    """Contains information about all PolymorphicIndexables in the project."""
    def __init__(self):
        self.all_models = {}
        self.families = {}

    def register(self, klass):
        """Adds a new PolymorphicIndexable to the registry."""
        doc_type = klass.search_objects.get_doctype()

        self.all_models[doc_type] = klass
        base_class = get_base_class(klass)
        if base_class not in self.families:
            self.families[base_class] = {}
        self.families[base_class][doc_type] = klass

    def get_doctypes(self, klass):
        """Returns all the mapping types for a given class."""
        base = get_base_class(klass)
        return self.families[base]

indexable_registry = IndexableRegistry()


class DJESConfig(AppConfig):
    name = 'djes'
    verbose_name = "DJ E.S."

    def ready(self):

        def register_subclasses(klass):
            for subclass in klass.__subclasses__():
                # only register concrete models
                meta = getattr(subclass, "_meta")
                if meta and not getattr(meta, "abstract"):
                    indexable_registry.register(subclass)
                register_subclasses(subclass)
        register_subclasses(Indexable)

    connections.configure(**settings.ES_CONNECTIONS)
