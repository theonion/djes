from django.db.models.signals import post_delete
from django.dispatch import receiver

from elasticsearch import TransportError

from .models import Indexable


@receiver(post_delete)
def delete_es_index_on_delete(sender, instance, **kwargs):
    if isinstance(instance, Indexable):
        try:
            instance.delete_index(ignore=404)
        except TransportError as e:
            raise(e)
