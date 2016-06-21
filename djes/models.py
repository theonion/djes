from django.db import models
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl.connections import connections

from .apps import indexable_registry
from .factory import shallow_class_factory
from .mapping import DjangoMapping, get_first_mapping
from .search import LazySearch


class IndexableManager(models.Manager):
    """a custom manager class to handle integration of native django models and elasticsearch storage
    """

    @property
    def client(self):
        """Get an elasticsearch client
        """
        if not hasattr(self, "_client"):
            self._client = connections.get_connection("default")
        return self._client

    @property
    def mapping(self):
        """Get a mapping class for this model

        This method will return a Mapping class for your model, generating it using settings from a
        `Mapping` class on your model (if one exists). The generated class is cached on the manager.
        """
        if not hasattr(self, "_mapping"):
            if hasattr(self.model, "Mapping"):
                mapping_klass = type("Mapping", (DjangoMapping, self.model.Mapping), {})
            else:
                mapping_klass = get_first_mapping(self.model)
                if mapping_klass is None:
                    mapping_klass = DjangoMapping
            self._mapping = mapping_klass(self.model)
        return self._mapping

    def from_es(self, hit):
        """Returns a Django model instance, using a document from Elasticsearch"""
        doc = hit.copy()
        klass = shallow_class_factory(self.model)

        # We can pass in the entire source, except when we have a non-indexable many-to-many
        for field in self.model._meta.get_fields():

            if not field.auto_created and field.many_to_many:
                if not issubclass(field.rel.to, Indexable):
                    if field.name in doc["_source"]:
                        del doc["_source"][field.name]

            # if field.one_to_many:
            #     if field.name in doc["_source"]:
            #         del doc["_source"][field.name]

        # Now let's go ahead and parse all the fields
        fields = self.mapping.properties.properties
        for key in fields:
            # TODO: What if we've mapped the property to a different name? Will we allow that?
            field = fields[key]

            # if isinstance(field, InnerObject):
            #     import pdb; pdb.set_trace()
            #     continue

            if doc["_source"].get(key):
                attribute_value = doc["_source"][key]

                doc["_source"][key] = field.to_python(attribute_value)

        return klass(**doc["_source"])

    def get(self, **kwargs):
        """Get a object from Elasticsearch by id
        """
        # get the doc id
        id = None
        if "id" in kwargs:
            id = kwargs["id"]
            del kwargs["id"]
        elif "pk" in kwargs:
            id = kwargs["pk"]
            del kwargs["pk"]
        else:
            raise self.model.DoesNotExist("You must provide an id to find")

        # connect to es and retrieve the document
        es = connections.get_connection("default")

        doc_type = self.model.search_objects.mapping.doc_type
        index = self.model.search_objects.mapping.index
        try:
            doc = es.get(index=index, doc_type=doc_type, id=id, **kwargs)
        except NotFoundError:
            message = "Can't find a document for {}, using id {}".format(
                doc_type, id)
            raise self.model.DoesNotExist(message)

        # parse and return
        return self.from_es(doc)

    def search(self):
        """
        """
        model_callbacks = {}
        indexes = []

        if self.model in indexable_registry.families:
            # There are child models...
            for doc_type, cls in indexable_registry.families[self.model].items():

                model_callbacks[doc_type] = cls.search_objects.from_es
                if cls.search_objects.mapping.index not in indexes:
                    indexes.append(cls.search_objects.mapping.index)
        else:
            # Just this one!
            model_callbacks[self.model.search_objects.mapping.doc_type] = self.from_es
            indexes.append(self.model.search_objects.mapping.index)

        return LazySearch().using(self.client).index(*indexes).doc_type(
            **model_callbacks)

    def refresh(self):
        """Force a refresh of the Elasticsearch index
        """
        self.client.indices.refresh(index=self.model.search_objects.mapping.index)


class Indexable(models.Model):
    """An abstract model that allows indexing and searching features
    """

    class Meta(object):
        abstract = True

    objects = models.Manager()
    search_objects = IndexableManager()

    def save(self, index=True, *args, **kwargs):
        super(Indexable, self).save(*args, **kwargs)
        if index:
            self.index()
        else:
            self.delete_index(ignore=[404])

    def to_dict(self):
        """Get a dictionary representation of this item, formatted for Elasticsearch"""
        out = {}

        fields = self.__class__.search_objects.mapping.properties.properties

        for key in fields:
            # TODO: What if we've mapped the property to a different name? Will we allow that?

            attribute = getattr(self, key)

            field = fields[key]

            # I believe this should take the highest priority.
            if hasattr(field, "to_es"):
                out[key] = field.to_es(attribute)

            # First we check it this is a manager, in which case we have many related objects
            elif isinstance(attribute, models.Manager):
                if issubclass(attribute.model, Indexable):
                    # TODO: We want this to have some awareness of the relevant field.
                    out[key] = [obj.to_dict() for obj in attribute.all()]
                else:
                    out[key] = list(attribute.values_list("pk", flat=True))

            elif callable(attribute):
                out[key] = attribute()

            elif isinstance(attribute, Indexable):
                out[key] = attribute.to_dict()
            else:
                out[key] = attribute

            if out[key] is None:
                del out[key]
        return out

    def index(self, refresh=False):
        """Indexes this object, using a document from `to_dict()`"""
        es = connections.get_connection("default")
        index = self.__class__.search_objects.mapping.index
        doc_type = self.__class__.search_objects.mapping.doc_type
        es.index(index, doc_type,
                 id=self.pk,
                 body=self.to_dict(),
                 refresh=refresh)

    def delete_index(self, refresh=False, ignore=None):
        """Removes the object from the index if `indexed=False`"""
        es = connections.get_connection("default")
        index = self.__class__.search_objects.mapping.index
        doc_type = self.__class__.search_objects.mapping.doc_type
        es.delete(index, doc_type, id=self.pk, refresh=refresh, ignore=ignore)

    @property
    def mapping(self):
        """Returns the proper mapping for this instance"""
        return self.__class__.search_objects.mapping

    @classmethod
    def is_orphaned(cls):
        manager = getattr(cls, 'search_objects', None)
        if not manager:
            return False
        mapping = getattr(manager, 'mapping', None)
        if not mapping:
            return False
        meta = getattr(mapping, 'Meta', None)
        if not meta:
            return False
        return getattr(meta, 'orphaned', False)

    @classmethod
    def get_base_class(cls):
        if cls.is_orphaned():
            return cls
        if cls.__bases__:
            for base in cls.__bases__:
                if base == Indexable:
                    return cls
                elif hasattr(base, "get_base_class"):
                    base_base = base.get_base_class()
                    if base_base:
                        return base_base
        return None

    @classmethod
    def get_doc_types(cls, exclude_base=False):
        """Returns the doc_type of this class and all of its descendants."""
        names = []
        if not exclude_base and hasattr(cls, 'search_objects'):
            if not getattr(cls.search_objects.mapping, "elastic_abstract", False):
                names.append(cls.search_objects.mapping.doc_type)
        for subclass in cls.__subclasses__():
            names += subclass.get_doc_types()
        return names
