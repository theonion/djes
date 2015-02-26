from django.apps import apps
from django.db import models
from django.db.backends import utils
from django.db.models.fields.related import RelatedField

from elasticsearch_dsl.mapping import Mapping
from elasticsearch_dsl.connections import connections

from .conf import settings

FIELD_MAPPINGS = {
    "AutoField": {"type": "long"},
    "OneToOneField": {"type": "long"},
    "IntegerField": {"type": "long"},
    "CharField": {"type": "string"},
    "TextField": {"type": "string"},
    "SlugField": {"type": "string", "index": "not_analyzed"},
    "ForeignKey": {"type": "long"}
}


def shallow_class_factory(model):
    if model._deferred:
        model = model._meta.proxy_for_model
    name = "%s_Shallow_%s" % (model.__name__, model.search_objects.get_doctype())
    name = utils.truncate_name(name, 80, 32)

    try:
        return apps.get_model(model._meta.app_label, name)

    except LookupError:

        class Meta:
            proxy = True
            app_label = model._meta.app_label

        overrides = {"save": None}
        overrides["Meta"] = Meta
        overrides["__module__"] = model.__module__
        overrides["_deferred"] = True
        return type(str(name), (model,), overrides)


def get_base_class(cls):
    while cls.__bases__[0] != Indexable:
        cls = cls.__bases__[0]
    return cls


class IndexableManager(models.Manager):

    def get_doctype(self):
        if hasattr(self.model.Elasticsearch, "doc_type"):
            return self.model.Elasticsearch.doc_type
        return "%s_%s" % (self.model._meta.app_label, self.model._meta.model_name)

    def get_index(self):
        if hasattr(self.model.Elasticsearch, "index"):
            return self.model.Elasticsearch.index
        return settings.ES_INDEX

    def get_mapping(self):
        mapping = Mapping(self.get_doctype())

        parent_pointer_fields = self.model._meta.parents.values()

        for field, model in self.model._meta.get_fields_with_model():

            if isinstance(field, models.ForeignKey):
                # This is a related field, so it should maybe be nested?

                # We only want to nest fields when they are indexable, and not parent pointers.
                if issubclass(field.rel.to, Indexable) and field not in parent_pointer_fields:
                    related_properties = field.rel.to.search_objects.get_mapping().properties.properties.to_dict()
                    mapping.field(field.name, {"type": "object", "properties": related_properties})
                    continue

            field_args = FIELD_MAPPINGS.get(field.get_internal_type())
            if field_args:
                # Do something
                db_column, attname = field.get_attname_column()
                mapping.field(db_column or attname, field_args)
            else:
                raise Exception("Can't find {}".format(field.get_internal_type()))

        mapping.properties._params["_id"] = {"path": self.model._meta.pk.name}

        return mapping

    def get(self, using=None, index=None, *args, **kwargs):
        id = None
        if len(args) == 1:
            id = args[0]
        else:
            id = kwargs.get("id") or kwargs.get("pk")

        if id is None:
            raise self.model.DoesNotExist("You must provide an id to find")

        es = connections.get_connection(using or "default")
        doc = es.get(
            index=index or self.get_index(),
            doc_type=self.get_doctype(),
            id=id,
            **kwargs
        )
        return self.from_es(doc)

    def from_es(self, hit):
        doc = hit.copy()
        doc.update(doc.pop('_source'))
        return self.model(**doc)  # Gonna need more than this, for the nested objects


class Indexable(models.Model):

    class Meta:
        abstract = True

    # def save(self):
    #     super(Indexable, self).save()

    objects = models.Manager()
    search_objects = IndexableManager()

    class Elasticsearch:
        pass

    def to_dict(self):
        out = {}
        for key in type(self).search_objects.get_mapping().properties.properties:
            # TODO: What if we've mapped the property to a different name?

            attribute = getattr(self, key)
            if callable(attribute):
                out[key] = attribute()
            elif isinstance(attribute, Indexable):
                out[key] = attribute.to_dict()
            else:
                out[key] = attribute
        return out
