from django.db.backends import utils
from django.db import models
from django.db.models.fields.related import ManyToOneRel, ForeignObjectRel
from django.apps import apps

from elasticsearch_dsl import field

from six import iteritems


class ElasticSearchForeignKey(object):

    def __init__(self, field_name, model):
        self.model = shallow_class_factory(model)
        self.field_name = field_name

    def __get__(self, instance, objtype=None):
        return instance.__dict__.get(self.field_name)

    def __set__(self, instance, value):
        if isinstance(value, field.InnerObjectWrapper):
            value = value.to_dict()
        instance.__dict__[self.field_name] = self.model(**value)


class ElasticSearchRelatedManager(object):

    def __init__(self, instances):
        self.instances = instances

    def count(self):
        return len(self.instances)

    def all(self):
        return self.instances


class ElasticSearchManyField(object):

    def __init__(self, field_name, model):
        self.model = shallow_class_factory(model)
        self.field_name = field_name

    def __get__(self, instance, objtype=None):
        if instance is None:
            return property()
        return instance.__dict__.get(self.field_name, ElasticSearchRelatedManager([]))

    def __set__(self, instance, value):
        value = [item.to_dict() for item in value if isinstance(item, field.InnerObjectWrapper)]
        instance.__dict__[self.field_name] = ElasticSearchRelatedManager([self.model(**item_data) for item_data in value])


class Test:

    def get(self):
        pass

    attr = property(get, set)


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

                if isinstance(dj_field, ManyToOneRel):
                    overrides[attname] = ElasticSearchManyField(attname, dj_field.related_model)
                elif isinstance(dj_field, ForeignObjectRel):
                    overrides[attname] = ElasticSearchForeignKey(attname, dj_field.related_model)

                if isinstance(dj_field, models.ManyToManyField):
                    overrides[attname] = ElasticSearchManyField(attname, dj_field.rel.to)

                if isinstance(dj_field, models.ForeignKey):
                    # Let's add a fake foreignkey attribute
                    overrides[attname] = ElasticSearchForeignKey(attname, dj_field.rel.to)

        return type(str(name), (model,), overrides)
