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


class SimpleObject(Indexable):

    foo = models.IntegerField()
    bar = models.CharField(max_length=255)
    baz = models.SlugField()


class ManualMappingObject(SimpleObject):

    qux = models.URLField()
    garbage = models.IntegerField()

    class Mapping:
        class Meta:
            doc_type = "super_manual_mapping"
            excludes = ("garbage",)

        bar = field.String(fields={"raw": field.String(index="not_analyzed")})


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
