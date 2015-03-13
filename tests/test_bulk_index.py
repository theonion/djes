from django.core import management
from elasticsearch_dsl.connections import connections
import pytest
from model_mommy import mommy
import time


from example.app.models import SimpleObject


@pytest.mark.django_db
def test_bulk_index():

    es = connections.get_connection("default")
    for index in ("djes-example_0001", "butts_0001"):
        es.indices.delete_alias(index, "_all", ignore=[404])
        es.indices.delete(index, ignore=[404])

    mommy.make(SimpleObject, _quantity=120)
    management.call_command("sync_es")

    response = es.search(
        index=SimpleObject.mapping.index,
        doc_type=SimpleObject.mapping.doc_type,
    )
    assert response["hits"]["total"] == 120

    for index in ("djes-example_0001", "butts_0001"):
        es.indices.delete_alias(index, "_all", ignore=[404])
        es.indices.delete(index, ignore=[404])
