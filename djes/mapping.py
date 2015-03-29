from django.db import models
from elasticsearch_dsl.mapping import Mapping

from djes.conf import settings

# TODO: expand this for all django field types
FIELD_MAPPINGS = {
    "AutoField": {"type": "long"},
    "OneToOneField": {"type": "long"},
    "IntegerField": {"type": "long"},
    "CharField": {"type": "string"},
    "TextField": {"type": "string"},
    "SlugField": {"type": "string", "index": "not_analyzed"},
    "DateTimeField": {"type": "date"},
    "DateField": {"type": "date"},
    "BooleanField": {"type": "boolean"}
}


class EmptyMeta(object):
    pass


class DjangoMapping(Mapping):
    """A subclass of the elasticsearch_dsl Mapping, allowing the automatic mapping
    of many fields on the model, while letting the developer override these settings"""

    def _build_m2m_fields(self):
        # Avoiding circular import
        excludes = getattr(self.Meta, "excludes", [])

        # First, let's get any many-to-many relations
        for field in self.model._meta.many_to_many:
            db_column, attname = field.get_attname_column()

            manual_field_mapping = getattr(self, attname, None)
            if manual_field_mapping:
                self.field(db_column, manual_field_mapping)
                continue

            # Checking to make sure this field hasn't been excluded
            if attname in excludes:
                continue

            if hasattr(field.rel.to, "from_es"):
                # If the related model is indexable, nest it
                related_properties = field.rel.to.mapping.properties.properties.to_dict()
                self.field(field.name, {"type": "nested", "properties": related_properties})
                continue
            else:
                # If it's not, let's just use a long
                self.field(db_column or attname, {"type": "long"})

    def __init__(self, model):
        # Avoiding circular import
        # from .models import Indexable

        self.model = model
        if not hasattr(self, "Meta"):
            self.Meta = EmptyMeta

        default_name = "{}_{}".format(self.model._meta.app_label, self.model._meta.model_name)
        name = getattr(self.Meta, "doc_type", default_name)

        super(DjangoMapping, self).__init__(name)
        self._meta = {}

        excludes = excludes = getattr(self.Meta, "excludes", [])

        # Now we add all the Django fields
        parent_pointer_fields = self.model._meta.parents.values()

        # First, let's get any many-to-many relations
        self._build_m2m_fields()

        # Now the rest of the fields
        for field, model in self.model._meta.get_fields_with_model():
            db_column, attname = field.get_attname_column()

            manual_field_mapping = getattr(self, attname, None)
            if manual_field_mapping:
                self.field(db_column, manual_field_mapping)
                continue

            # Checking to make sure this field hasn't been excluded
            if attname in excludes:
                continue

            if isinstance(field, models.ForeignKey):
                # This is a related field, so it should maybe be nested?

                # We only want to nest fields when they are indexable, and not parent pointers.
                if hasattr(field.rel.to, "from_es") and field not in parent_pointer_fields:
                    related_properties = field.rel.to.mapping.properties.properties.to_dict()
                    self.field(field.name, {"type": "nested", "properties": related_properties})
                    continue
                else:
                    self.field(db_column or attname, {"type": "long"})
                    continue

            field_args = FIELD_MAPPINGS.get(field.get_internal_type())
            if field_args:
                # Do something
                self.field(db_column or attname, field_args)
            else:
                raise Warning("Can't find {}".format(field.get_internal_type()))

        self.properties._params["_id"] = {"path": self.model._meta.pk.name}
        if getattr(self.Meta, "dynamic", "strict") == "strict":
            self.properties._params["dynamic"] = "strict"

    @property
    def index(self):
        return getattr(self.Meta, "index", settings.ES_INDEX)
