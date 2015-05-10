from django.db.backends import utils
from django.db import models
from django.apps import apps

from elasticsearch_dsl import field

from six import iteritems


class ElasticSearchForeignKey(object):

    def __init__(self, model):
        self.model = shallow_class_factory(model)
        self.instance = None
        self.name = None

    def set(self, name, data):
        if data:
            self.instance = self.model(**data)
            self.name = name

    def get(self, parent_class):
        return self.instance


class ElasticSearchRelatedManager(object):
    def __init__(self, model):
        self.model = shallow_class_factory(model)
        self.instances = None
        self.name = None

    def set(self, name, data):
        self.instances = [self.model(**item_data) for item_data in data]
        self.name = name

    def get(self, parent_class):
        return self

    def all(self):
        return self.instances

    def count(self):
        return len(self.instances)


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

        for attname, es_field in iteritems(model.search_objects.mapping.properties._params["properties"]):
            if type(es_field) == field.Nested:
                # This is a nested object!
                dj_field = model._meta.get_field(attname)

                if isinstance(dj_field, models.ManyToManyField):
                    mock_fkey = ElasticSearchRelatedManager(dj_field.rel.to)
                    overrides[attname] = property(mock_fkey.get, mock_fkey.set)

                if isinstance(dj_field, models.ForeignKey):
                    # Let's add a fake foreignkey attribute
                    mock_fkey = ElasticSearchForeignKey(dj_field.rel.to)
                    overrides[attname] = property(mock_fkey.get, mock_fkey.set)

        return type(str(name), (model,), overrides)
