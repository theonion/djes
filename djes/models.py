from django.apps import apps
from django.db import models
from django.db.backends import utils

from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import field
from elasticsearch.exceptions import NotFoundError

from six import iteritems


class ElasticSearchForeignKey(object):

    def __init__(self, model):
        self.model = shallow_class_factory(model)
        self.instance = None
        self.name = None

    def set(self, name, data):
        self.instance = self.model(**data)
        self.name = name

    def get(self, parent_class):
        return self.instance


def shallow_class_factory(model):
    if model._deferred:
        model = model._meta.proxy_for_model
    name = "{}_ElasticSearchResult".format(model.__name__)
    name = utils.truncate_name(name, 80, 32)
    # try to get the model from the django registry
    try:
        return apps.get_model(model._meta.app_label, name)
    # get the object's type - hopefully a django model
    except LookupError:
        class Meta(object):
            proxy = True
            app_label = model._meta.app_label

        overrides = {
            "save": None,
            "Meta": Meta,
            "__module__": model.__module__,
            "_deferred": True,
        }

        for attname, es_field in iteritems(model.mapping.properties._params["properties"]):
            if type(es_field) == field.Object:
                # This is a nested object!
                dj_field = model._meta.get_field(attname)
                if isinstance(dj_field, models.ForeignKey):
                    # Let's add a fake foreignkey attribute
                    mock_fkey = ElasticSearchForeignKey(dj_field.rel.to)
                    overrides[attname] = property(mock_fkey.get, mock_fkey.set)

        return type(str(name), (model,), overrides)


class IndexableManager(models.Manager):
    """a custom manager class to handle integration of native django models and elasticsearch storage
    """

    def get(self, *args, **kwargs):
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
        if len(args) == 1:
            id = args[0]
        elif "id" in kwargs:
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
        return self.from_es(doc)

    def from_es(self, hit):
        doc = hit.copy()
        klass = shallow_class_factory(self.model)

        return klass(**doc["_source"])  # Gonna need more than this, for the nested objects


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
            if callable(attribute):
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
