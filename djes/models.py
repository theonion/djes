from django.db import models
from django.db.models.fields.related import RelatedField

from elasticsearch_dsl.mapping import Mapping


FIELD_MAPPINGS = {
    "AutoField": {"type": "long"},
    "OneToOneField": {"type": "long"},
    "IntegerField": {"type": "long"},
    "CharField": {"type": "string"},
    "TextField": {"type": "string"},
    "SlugField": {"type": "string", "index": "not_analyzed"},
    "ForeignKey": {"type": "long"}
}


def get_base_class(cls):
    while cls.__bases__[0] != Indexable:
        cls = cls.__bases__[0]
    return cls


class IndexableManager(models.Manager):

    def get_doctype(self):
        if hasattr(self.model.Elasticsearch, "doc_type"):
            return self.model.Elasticsearch.doc_type
        return "%s_%s" % (self.model._meta.app_label, self.model._meta.model_name)

    def get_mapping(self):
        mapping = Mapping(self.get_doctype())

        for field, model in self.model._meta.get_fields_with_model():

            if isinstance(field, models.ForeignKey):
                # Related, let's check the model

                if issubclass(field.rel.to, Indexable) and not issubclass(self.model, field.rel.to):
                    related_mapping = field.rel.to.search_objects.get_mapping()
                    related_doctype = field.rel.to.search_objects.get_doctype()
                    related_properties = related_mapping.to_dict()[related_doctype]["properties"]
                    mapping.field(field.name, {"type": "object", "properties": related_properties})
                    continue

            field_args = FIELD_MAPPINGS.get(field.get_internal_type())
            if field_args:
                # Do something
                db_column, attname = field.get_attname_column()
                mapping.field(db_column or attname, field_args)
            else:
                print(field)
                raise Exception("Can't find {}".format(field.get_internal_type()))

        mapping.properties._params["_id"] = {"path": self.model._meta.pk.name}

        return mapping


class Indexable(models.Model):
    class Meta:
        abstract = True

    search_objects = IndexableManager()

    def save(self):
        super(Indexable, self).save()

    class Elasticsearch:
        pass
