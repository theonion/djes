from django.db import models

from djes.models import Indexable

from elasticsearch_dsl import field


class ColorField(field.Object):
    """Just a sample custom field. In this case, a CharField that's formatted
    something like "#FFDDEE"."""

    def __init__(self, *args, **kwargs):
        super(ColorField, self).__init__(*args, **kwargs)
        self.properties["red"] = field.construct_field("string")
        self.properties["green"] = field.construct_field("string")
        self.properties["blue"] = field.construct_field("string")

    def to_es(self, data):
        red = data[1:3]
        green = data[3:5]
        blue = data[5:7]

        return {
            "red": red,
            "green": green,
            "blue": blue
        }

    def to_python(self, data):
        return "#{red}{green}{blue}".format(**data)


class PolyParentField(field.Object):

    def to_es(self, data):
        return self.get_poly_object(data).to_dict()

    def get_poly_object(self, data):
        cls = data.get_base_class()
        for subclass in cls.__subclasses__():
            model_name = subclass._meta.model_name
            child = getattr(data, model_name, None)
            if child:
                return child
        return data


class SimpleObject(Indexable):

    foo = models.IntegerField()
    bar = models.CharField(max_length=255)
    baz = models.SlugField()
    published = models.DateTimeField(null=True, blank=True)


class ManualMappingObject(SimpleObject):

    qux = models.URLField()
    garbage = models.IntegerField()

    @property
    def status(self):
        return "final"

    class Mapping:
        class Meta:
            doc_type = "super_manual_mapping"
            excludes = ("garbage",)

        bar = field.String(fields={"raw": field.String(index="not_analyzed")})
        status = field.String(index="not_analyzed")


class PolyParent(Indexable):

    text = models.CharField(max_length=255)

    @classmethod
    def get_merged_mapping_properties(cls):
        properties = {}
        def gather_properties(klass):
            properties.update(klass.search_objects.mapping.to_dict())
            for subclass in klass.__subclasses__():
                gather_properties(subclass)
        gather_properties(cls)
        return properties


class PolyChildA(PolyParent):

    slug = models.CharField(max_length=255)
    number = models.IntegerField()

    @property
    def slug_number(self):
        return "%s-%s"


class PolyChildB(PolyParent):

    album = models.CharField(max_length=255)
    band_name = models.CharField(max_length=255)

    @property
    def full_title(self):
        return self.full_title


class PolyRelationship(Indexable):

    poly_parent = models.ForeignKey(PolyParent)

    class Mapping:
        poly_parent = PolyParentField()

        class Meta:
            dynamic = False


class ChildObject(SimpleObject):

    trash = models.TextField()

    class Mapping:
        trash = field.String(analyzer="snowball")


class GrandchildObject(ChildObject):

    qux = models.URLField()


class CustomFieldObject(Indexable):

    color = models.CharField(max_length=7)

    class Mapping:
        color = ColorField()


class RelatedSimpleObject(models.Model):

    datums = models.TextField()


class RelatedNestedObject(Indexable):

    denormalized_datums = models.TextField()


class RelatableObject(Indexable):

    name = models.CharField(max_length=255)
    simple = models.ForeignKey(RelatedSimpleObject)
    nested = models.ForeignKey(RelatedNestedObject)


class Tag(Indexable):
    name = models.CharField(max_length=255)


class DumbTag(models.Model):
    name = models.CharField(max_length=255)


class RelationsTestObject(Indexable):
    data = models.CharField(max_length=255)
    tags = models.ManyToManyField(Tag, related_name="tag")
    dumb_tags = models.ManyToManyField(DumbTag, related_name="dumb_tags")


class SelfRelation(Indexable):

    name = models.CharField(max_length=255)
    related = models.ForeignKey("self")

    class Mapping:
        class Meta:
            excludes = ("related",)


class ReverseRelationsParentObject(Indexable):
    name = models.CharField(max_length=255)

    class Mapping:

        class Meta:
            includes = ("children",)

class ReverseRelationsChildObject(Indexable):

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(ReverseRelationsParentObject, related_name="children")

    class Mapping:

        class Meta:
            excludes = ("parent",)
