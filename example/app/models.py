from django.db import models

from djes.models import Indexable


class SimpleObject(Indexable):

    foo = models.IntegerField()
    bar = models.CharField(max_length=255)
    baz = models.SlugField()


class ManualMappingObject(SimpleObject):

    class Elasticsearch:
        doc_type = "super_manual_mapping"
