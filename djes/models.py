from django.db import models

from elasticsearch_dsl.mapping import Mapping


FIELD_MAPPINGS = {
    "AutoField": {"type": "long"},
    "IntegerField": {"type": "long"},
    "CharField": {"type": "string"},
    "SlugField": {"type": "string", "index": "not_analyzed"}
}


def get_base_class(cls):
    while cls.__bases__[0] != Indexable:
        cls = cls.__bases__[0]
    return cls


class ElasticsearchMeta(object):

    def __init__(self, model):
        self.model = model

    def get_object(self):
        pass


class IndexableManager(models.Manager):

    def get_doctype(self):
        if hasattr(self.model.ElasticSearch, "doc_type"):
            return self.model.ElasticSearch.doc_type
        return "%s_%s" % (self.model._meta.app_label, self.model._meta.model_name)

    def get_mapping(self):
        mapping = Mapping(self.get_doctype())

        for field, model in self.model._meta.get_fields_with_model():
            field_args = FIELD_MAPPINGS.get(field.get_internal_type())
            if field_args:
                # Do something
                mapping.field(field.name, field_args)

        mapping.properties._params["_id"] = {"path": self.model._meta.pk.name}

        return mapping



class Indexable(models.Model):
    class Meta:
        abstract = True

    search_objects = IndexableManager()

    def save(self):
        super(Indexable, self).save()

    class ElasticSearch:
        pass
