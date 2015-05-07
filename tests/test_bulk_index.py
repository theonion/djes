from django.core import management
import pytest
from model_mommy import mommy
import time

from example.app.models import SimpleObject


@pytest.mark.django_db
def test_bulk_index(es_client):

    mommy.make(SimpleObject, _quantity=120)
    management.call_command("sync_es")
    management.call_command("bulk_index")
    time.sleep(1)  # Let the index refresh

    response = es_client.search(
        index=SimpleObject.search_objects.mapping.index,
        doc_type=SimpleObject.search_objects.mapping.doc_type,
    )
    assert response["hits"]["total"] == 120
