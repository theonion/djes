from django.core import management
import pytest
from model_mommy import mommy
import time

from example.app.models import SimpleObject, ManualMappingObject


@pytest.mark.django_db
def test_simple_get(es_client):

    management.call_command("sync_es")

    mommy.make(SimpleObject, _quantity=10)
    mommy.make(ManualMappingObject, _quantity=5)
    SimpleObject.search_objects.refresh()

    assert SimpleObject.search_objects.search().count() == 15
    assert len(SimpleObject.search_objects.search()) == 15
    assert ManualMappingObject.search_objects.search().count() == 5
    assert len(ManualMappingObject.search_objects.search()) == 5

    es_obj = ManualMappingObject.search_objects.search()[0]
    db_obj = ManualMappingObject.objects.get(id=es_obj.id)
    assert es_obj.id == db_obj.id
    assert es_obj.qux == db_obj.qux
    assert es_obj.garbage is None  # This one isn't indexed...

    for obj in SimpleObject.search_objects.search():
        assert isinstance(obj, SimpleObject)

@pytest.mark.django_db
def test_full_search(es_client):
    management.call_command("sync_es")

    mommy.make(SimpleObject, _quantity=10)
    mommy.make(ManualMappingObject, _quantity=5)
    SimpleObject.search_objects.refresh()

    assert SimpleObject.search_objects.search().full().count() == 15
    assert len(SimpleObject.search_objects.search().full()) == 15
    assert ManualMappingObject.search_objects.search().full().count() == 5
    assert len(ManualMappingObject.search_objects.search().full()) == 5

    es_obj = ManualMappingObject.search_objects.search().full()[0]
    db_obj = ManualMappingObject.objects.get(id=es_obj.id)
    assert es_obj.id == db_obj.id
    assert es_obj.qux == db_obj.qux
    assert es_obj.garbage == db_obj.garbage  # This one isn't indexed, but this is a full search

    for obj in SimpleObject.search_objects.search().full():
        assert isinstance(obj, SimpleObject)
