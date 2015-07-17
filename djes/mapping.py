from django.db import models
from django.db.models.fields.related import ManyToOneRel, ForeignObjectRel

from elasticsearch_dsl.mapping import Mapping
from elasticsearch_dsl.field import Field

from djes.conf import settings

FIELD_MAPPINGS = {
    "AutoField": {"type": "long"},
    "BigIntegerField": {"type": "long"},
    "BinaryField": {"type": "binary"},
    "BooleanField": {"type": "boolean"},
    "CharField": {"type": "string"},
    "CommaSeparatedIntegerField": {"type": "string"},
    "DateField": {"type": "date"},
    "DateTimeField": {"type": "date"},
    "DecimalField": {"type": "string"},
    "DurationField": {"type": "long"},
    "EmailField": {"type": "string"},
    # "FileField": {"type": ""},  # TODO: make a decision on this
    "FilePathField": {"type": "string"},
    "FloatField": {"type": "double"},
    # "ImageField": {"type": ""},  # TODO: make a decision on this
    "IntegerField": {"type": "long"},
    "IPAddressField": {"type": "string", "index": "not_analyzed"},
    "GenericIPAddressField": {"type": "string", "index": "not_analyzed"},
    "NullBooleanField": {"type": "boolean"},
    "PositiveIntegerField": {"type": "long"},
    "PositiveSmallIntegerField": {"type": "long"},
    "SlugField": {"type": "string", "index": "not_analyzed"},
    "SmallIntegerField": {"type": "long"},
    "TextField": {"type": "string"},
    "TimeField": {"type": "string"},
    "URLField": {"type": "string"},
    "UUIDField": {"type": "string", "index": "not_analyzed"},
    "ForeignKey": {"type": "long"},
    "ManyToManyField": {"type": "long"},
    "OneToOneField": {"type": "long"},
}


def get_first_mapping(cls):
    """This allows for Django-like inheritance of mapping configurations"""
    from .models import Indexable

    if issubclass(cls, Indexable) and hasattr(cls, "Mapping"):
        return cls.Mapping
    for base in cls.__bases__:
        mapping = get_first_mapping(base)
        if mapping:
            return mapping
    return None


class EmptyMeta(object):
    pass


class DjangoMapping(Mapping):
    """A subclass of the elasticsearch_dsl Mapping, allowing the automatic mapping
    of many fields on the model, while letting the developer override these settings"""

    def __init__(self, model):
        from .models import Indexable

        self.model = model
        if not hasattr(self, "Meta"):
            self.Meta = EmptyMeta

        default_name = "{}_{}".format(self.model._meta.app_label, self.model._meta.model_name)
        name = getattr(self.Meta, "doc_type", default_name)

        super(DjangoMapping, self).__init__(name)
        self._meta = {}

        excludes = getattr(self.Meta, "excludes", [])
        includes = getattr(self.Meta, "includes", [])

        for field in self.model._meta.get_fields():

            if field.auto_created and field.is_relation:
                if not hasattr(field, "rel") or not field.rel.parent_link:
                    continue

            db_column, attname = field.db_column, field.attname

            manual_field_mapping = getattr(self, field.name, None)
            # TODO: I am 90% shirt this is not being utilized. Test later.
            if manual_field_mapping:
                self.field(field.name, manual_field_mapping)
                continue

            if field.name in excludes:
                continue

            self.configure_field(field)

        # Now any included relations
        for name in includes:
            field = self.model._meta.get_field(name)
            self.configure_field(field)

        # Now any custom fields
        for field in dir(self.__class__):
            manual_field_mapping = getattr(self, field)
            if field not in self.properties.properties.to_dict() and isinstance(manual_field_mapping, Field):
                self.field(field, manual_field_mapping)

        if getattr(self.Meta, "dynamic", "strict") == "strict":
            self.properties._params["dynamic"] = "strict"


    def configure_field(self, field):
        """This configures an Elasticsearch Mapping field, based on a Django model field"""
        from .models import Indexable

        # This is for reverse relations, which do not have a db column
        if field.auto_created and field.is_relation:
            if isinstance(field, (ForeignObjectRel, ManyToOneRel)) and issubclass(field.related_model, Indexable):
                related_properties = field.related_model.search_objects.mapping.properties.properties.to_dict()
                self.field(field.name, {"type": "nested", "properties": related_properties})
                return

        if field.get_internal_type() == "ManyToManyField" and issubclass(field.rel.to, Indexable):

            related_properties = field.rel.to.search_objects.mapping.properties.properties.to_dict()
            self.field(field.name, {"type": "nested", "properties": related_properties})
            return

        if isinstance(field, models.ForeignKey):
            # This is a related field, so it should maybe be nested?

            # We only want to nest fields when they are indexable, and not parent pointers.
            if issubclass(field.rel.to, Indexable) and not field.rel.parent_link:

                related_properties = field.rel.to.search_objects.mapping.properties.properties.to_dict()
                self.field(field.name, {"type": "nested", "properties": related_properties})
                return

        db_column, attname = field.db_column, field.attname

        field_args = FIELD_MAPPINGS.get(field.get_internal_type())
        if field_args:
            self.field(db_column or attname, field_args)
        else:
            raise Warning("Can't find {}".format(field.get_internal_type()))


    @property
    def index(self):
        return getattr(self.Meta, "index", settings.ES_INDEX)
