from django.apps import apps
from django.db import models
from django.db.backends import utils

from elasticsearch_dsl.connections import connections


def shallow_class_factory(model):
    """finds the class for a given model

    :param model: an Indexable django model
    :type model: django.db.models.Model

    :return: the class of the model
    :rtype: django.db.models.Model
    """
    if model._deferred:
        model = model._meta.proxy_for_model
    name = "%s_Shallow_%s" % (model.__name__, model.search_objects.get_doctype())
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
        else:
            id = kwargs.get("id") or kwargs.get("pk")
        if id is None:
            raise self.model.DoesNotExist("You must provide an id to find")

        # connect to es and retrieve the document
        es = connections.get_connection(using or "default")
        doc = es.get(
            index=self.model.mapping.index,
            doc_type=self.model.doc_type,
            id=id,
            **kwargs
        )

        # parse and return
        return self.from_es(doc)

    def from_es(self, hit):
        """copies the result of an elasticsearch search result and adds its `_source` to the top level of the body

        :param hit: the result of an elasticsearch search
        :type hit: dict

        :return: the result of an elasticsearch search result and adds its `_source` to the top level of the body
        :rtype: dict
        """
        doc = hit.copy()
        doc.update(doc.pop('_source'))
        return self.model(**doc)  # Gonna need more than this, for the nested objects


class Indexable(models.Model):
    """an abstract django model to tie in elasticsearch capabilities
    """

    class Meta(object):
        abstract = True

    objects = models.Manager()
    search_objects = IndexableManager()

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
