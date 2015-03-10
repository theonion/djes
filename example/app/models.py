from django.db import models

from djes.models import Indexable
from djes.mapping import DjangoMapping

from elasticsearch_dsl import field


class SimpleObject(Indexable):

    foo = models.IntegerField()
    bar = models.CharField(max_length=255)
    baz = models.SlugField()


class ManualMapping(DjangoMapping):
    class Meta:
        doc_type = "super_manual_mapping"

    bar = field.String(fields={"raw": field.String(index="not_analyzed")})


class ManualMappingObject(SimpleObject):

    qux = models.URLField()

    mapping = ManualMapping


class RelatedSimpleObject(models.Model):

    datums = models.TextField()


class RelatedNestedObject(Indexable):

    denormalized_datums = models.TextField()


class RelatableObject(Indexable):

    name = models.CharField(max_length=255)
    simple = models.ForeignKey(RelatedSimpleObject)
    nested = models.ForeignKey(RelatedNestedObject)
