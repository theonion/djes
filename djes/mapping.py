from django.db import models

from elasticsearch_dsl.mapping import Mapping, Properties


FIELD_MAPPINGS = {
    "AutoField": {"type": "long"},
    "OneToOneField": {"type": "long"},
    "IntegerField": {"type": "long"},
    "CharField": {"type": "string"},
    "TextField": {"type": "string"},
    "SlugField": {"type": "string", "index": "not_analyzed"},
    "ForeignKey": {"type": "long"}
}


class DjangoMapping(Mapping):
    """A subclass of the elasticsearch_dsl Mapping, allowing the automatic mapping
    of many fields on the model, while letting the developer override these settings"""

    def __init__(self, model):
        # Avoiding circular import
        from .models import Indexable

        self.model = model
        # todo: Check for Meta override?
        if hasattr(self, "Meta") and self.Meta.doc_type:
            name = self.Meta.doc_type
        else:
            name = "{}_{}".format(self.model._meta.app_label, self.model._meta.model_name)
        
        super(DjangoMapping, self).__init__(name)
        self._meta = {}

        # Now we add all the Django fields
        parent_pointer_fields = self.model._meta.parents.values()

        for field, model in self.model._meta.get_fields_with_model():
            if isinstance(field, models.ForeignKey):
                # This is a related field, so it should maybe be nested?

                # We only want to nest fields when they are indexable, and not parent pointers.
                if issubclass(field.rel.to, Indexable) and field not in parent_pointer_fields:
                    related_properties = field.rel.to.search_objects.get_mapping().properties.properties.to_dict()
                    self.field(field.name, {"type": "object", "properties": related_properties})
                    continue

            field_args = FIELD_MAPPINGS.get(field.get_internal_type())
            if field_args:
                # Do something
                db_column, attname = field.get_attname_column()
                self.field(db_column or attname, field_args)
            else:
                raise Exception("Can't find {}".format(field.get_internal_type()))

        self.properties._params["_id"] = {"path": self.model._meta.pk.name}
