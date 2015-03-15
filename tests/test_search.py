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
    time.sleep(2)  # Let the index refresh

    assert SimpleObject.search_objects.search().count() == 15
    assert ManualMappingObject.search_objects.search().count() == 5

    es_obj = ManualMappingObject.search_objects.search().execute()[0]
    db_obj = ManualMappingObject.objects.get(id=es_obj.id)
    assert es_obj.id == db_obj.id
    assert es_obj.qux == db_obj.qux
    assert es_obj.garbage is None  # This one isn't indexed...
