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


def get_doctype(model):
    if hasattr(model.ElasticSearch, "doc_type"):
        return model.ElasticSearch.doc_type
    return "%s_%s" % (model._meta.app_label, model._meta.model_name)


def get_mapping_object(klass):

    mapping = Mapping(get_doctype(klass))

    for field, model in klass._meta.get_fields_with_model():
        field_args = FIELD_MAPPINGS.get(field.get_internal_type())
        if field_args:
            # Do something
            mapping.field(field.name, field_args)

    mapping.properties._params["_id"] = {"path": klass._meta.pk.name}

    return mapping


class IndexableManager(models.Manager):

    def get_mapping(self):
        return get_mapping_object(self.model)


class Indexable(models.Model):
    class Meta:
        abstract = True

    search_objects = IndexableManager()

    def save(self):
        super(Indexable, self).save()

    class ElasticSearch:
        pass
