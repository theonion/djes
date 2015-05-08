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
        if not hasattr(self, "_client"):
            self._client = connections.get_connection("default")
        return self._client

    @property
    def mapping(self):
        if not hasattr(self, "_mapping"):
            if hasattr(self.model, "Mapping"):
                mapping_klass = type("Mapping", (DjangoMapping, self.model.Mapping), {})
            else:
                mapping_klass = get_first_mapping(self.model)
                if mapping_klass is None:
                    mapping_klass = DjangoMapping
            self._mapping = mapping_klass(self.model)
        return self._mapping

    def get(self, **kwargs):
        """gets a specific document from elasticsearch

        :return: the result of the search
        :rtype: dict

        :keyword id: the id of the model/document
        :type id: int or str

        :keyword pk: the id of the model/document
        :type pd: int or str
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
        return self.model.from_es(doc)

    def search(self):
        model_callbacks = {}
        indexes = []

        if self.model in indexable_registry.families:
            # There are child models...
            for doc_type, cls in indexable_registry.families[self.model].items():

                model_callbacks[doc_type] = cls.from_es
                if cls.search_objects.mapping.index not in indexes:
                    indexes.append(cls.search_objects.mapping.index)
        else:
            # Just this one!
            model_callbacks[self.model.search_objects.mapping.doc_type] = self.model.from_es
            indexes.append(self.model.search_objects.mapping.index)

        return LazySearch().using(self.client).index(*indexes).doc_type(
            **model_callbacks)

    def refresh(self):
        self.client.indices.refresh(index=self.model.search_objects.mapping.index)


class Indexable(models.Model):
    """an abstract django model to tie in elasticsearch capabilities
    """

    class Meta(object):
        abstract = True

    objects = models.Manager()
    search_objects = IndexableManager()

    def save(self, index=True, *args, **kwargs):
        super(Indexable, self).save(*args, **kwargs)
        if index:
            self.index()

    def to_dict(self):
        """converts the django model's fields to an elasticsearch mapping

        :return: an elasticsearch mapping
        :rtype: elasticsearch_dsl.mapping.Mapping
        """
        out = {}

        fields = self.__class__.search_objects.mapping.properties.properties

        for key in fields:
            # TODO: What if we've mapped the property to a different name? Will we allow that?

            attribute = getattr(self, key)

            field = fields[key]

            # First we check it this is a manager, in which case we have many related objects
            if isinstance(attribute, models.Manager):
                if issubclass(attribute.model, Indexable):
                    out[key] = [obj.to_dict() for obj in attribute.all()]
                else:
                    out[key] = list(attribute.values_list("pk", flat=True))

            elif callable(attribute):
                out[key] = attribute()
            elif isinstance(attribute, Indexable):
                out[key] = attribute.to_dict()
            elif hasattr(field, "to_es"):
                out[key] = field.to_es(attribute)
            else:
                out[key] = attribute
        return out

    def index(self, refresh=False):
        """Indexes this object"""
        es = connections.get_connection("default")
        index = self.__class__.search_objects.mapping.index
        doc_type = self.__class__.search_objects.mapping.doc_type
        es.index(index, doc_type,
                 id=self.pk,
                 body=self.to_dict(),
                 refresh=refresh)

    @classmethod
    def from_es(cls, hit):
        doc = hit.copy()
        klass = shallow_class_factory(cls)

        # We can pass in the entire source, except in the case that we have a many-to-many
        local_many_to_many_fields = {}
        for field in cls._meta.local_many_to_many:
            local_many_to_many_fields[field.get_attname_column()[1]] = field

        to_be_deleted = []
        for name, value in doc["_source"].items():
            if name in local_many_to_many_fields:
                field = local_many_to_many_fields[name]
                if not hasattr(field.rel.to, "from_es"):
                    to_be_deleted.append(name)

        for name in to_be_deleted:
            del doc["_source"][name]

        return klass(**doc["_source"])

    @classmethod
    def get_base_class(cls):
        if cls.__bases__:
            for base in cls.__bases__:
                if base == Indexable:
                    return cls
                elif hasattr(base, "get_base_class"):
                    base_base = base.get_base_class()
                    if base_base:
                        return base_base
        return None
