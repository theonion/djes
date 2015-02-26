from django.db import models
from example.app.models import SimpleObject, ManualMappingObject, RelatableObject, RelatedSimpleObject, RelatedNestedObject


def test_model():

    for field, model in ManualMappingObject._meta.get_fields_with_model():

        if isinstance(field, models.ForeignKey):
            # Related, let's check the model
            print(field)
            print(dir(field))
            print(ManualMappingObject._meta.parents.keys())

            # if issubclass(field.rel.to, Indexable) and not issubclass(self.model, field.rel.to):
            #     related_mapping = field.rel.to.search_objects.get_mapping()
            #     related_doctype = field.rel.to.search_objects.get_doctype()
            #     related_properties = related_mapping.to_dict()[related_doctype]["properties"]
            #     mapping.field(field.name, {"type": "object", "properties": related_properties})
            #     continue

    raise Exception("blergh")
