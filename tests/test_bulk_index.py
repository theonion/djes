from django.core import management
import pytest
from model_mommy import mommy
import time

from example.app.models import SimpleObject

from djes.management.commands.bulk_index import model_iterator


@pytest.mark.django_db
def test_model_iterator(es_client):
    mommy.make(SimpleObject)
    for action_doc in model_iterator(SimpleObject, index="djes-example_0001"):
        assert action_doc["_index"] == "djes-example_0001"
        assert action_doc["_type"] == "app_simpleobject"


@pytest.mark.django_db
def test_bulk_index(es_client):
    mommy.make(SimpleObject, _quantity=120)
    management.call_command("sync_es")
    management.call_command("bulk_index")
    time.sleep(1)  # Let the index refresh

    response = es_client.search(
        index=SimpleObject.search_objects.mapping.index,
        doc_type=SimpleObject.search_objects.mapping.doc_type
    )
    assert response["hits"]["total"] == 120
