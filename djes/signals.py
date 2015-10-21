from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Indexable


@receiver(post_delete)
def delete_es_index_on_delete(sender, instance, **kwargs):
    if isinstance(instance, Indexable):
        instance.delete_index()
