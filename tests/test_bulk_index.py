from django.core import management

import pytest
import time
from model_mommy import mommy

from djes.management.commands.bulk_index import model_iterator

from example.app.models import SimpleObject


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


@pytest.mark.django_db
def test_bulk_index_called_in_sync_es(es_client):
    mommy.make(SimpleObject, _quantity=120)

    # TODO: weird race condition with fixtures recreating the indices.
    es_client.indices.delete("djes-example*", ignore=[404])
    assert es_client.indices.exists_alias(name='djes-example') is False
    assert es_client.indices.exists('djes-example_0001') is False
    management.call_command("sync_es")
    assert es_client.indices.exists_alias(name='djes-example') is True
    assert es_client.indices.exists('djes-example_0001') is True
