from django.db import models

from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import Search
from elasticsearch.exceptions import NotFoundError

from .apps import indexable_registry

from .factory import shallow_class_factory


class IndexableManager(models.Manager):
    """a custom manager class to handle integration of native django models and elasticsearch storage
    """

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

        doc_type = self.model.mapping.doc_type
        index = self.model.mapping.index
        try:
            doc = es.get(
                index=index,
                doc_type=doc_type,
                id=id,
                **kwargs
            )
        except NotFoundError:
            message = "Can't find a document for {}, using id {}".format(doc_type, id)
            raise self.model.DoesNotExist(message)

        # parse and return
        return self.model.from_es(doc)

    def search(self):
        client = connections.get_connection("default")

        model_callbacks = {}
        indexes = []

        if self.model in indexable_registry.families:
            # There are child models...
            for doc_type, cls in indexable_registry.families[self.model].items():

                model_callbacks[doc_type] = cls.from_es
                indexes.append(cls.mapping.index)
        else:
            # Just this one!
            model_callbacks[self.model.mapping.doc_type] = self.model.from_es
            indexes.append(self.model.mapping.index)

        return Search().using(client).index(*indexes).doc_type(**model_callbacks)


class Indexable(models.Model):
    """an abstract django model to tie in elasticsearch capabilities
    """

    class Meta(object):
        abstract = True

    objects = models.Manager()
    search_objects = IndexableManager()

    def save(self, *args, **kwargs):
        super(Indexable, self).save(*args, **kwargs)
        self.index()

    def to_dict(self):
        """converts the django model's fields to an elasticsearch mapping

        :return: an elasticsearch mapping
        :rtype: elasticsearch_dsl.mapping.Mapping
        """
        out = {}
        for key in self.mapping.properties.properties:
            # TODO: What if we've mapped the property to a different name? Will we allow that?

            attribute = getattr(self, key)

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
            else:
                out[key] = attribute
        return out

    def index(self, refresh=False):
        """Indexes this object"""
        es = connections.get_connection("default")
        es.index(self.mapping.index, self.mapping.doc_type, body=self.to_dict(), refresh=refresh)

    @classmethod
    def from_es(cls, hit):
        doc = hit.copy()
        klass = shallow_class_factory(cls)

        # We can pass in the entire source, except in the case that we have a many-to-many
        local_many_to_many_fields = {}
        for field in cls._meta.local_many_to_many:
            local_many_to_many_fields[field.get_attname_column()[1]] = field

        for name, value in hit["_source"].items():
            if name in local_many_to_many_fields:
                field = local_many_to_many_fields[name]
                if not hasattr(field.rel.to, "from_es"):
                    del doc["_source"][name]

        return klass(**doc["_source"])

    @classmethod
    def get_base_class(cls):
        while cls.__bases__ and cls.__bases__[0] != Indexable:
            cls = cls.__bases__[0]
        return cls
