from django.core import management
import pytest
from model_mommy import mommy
import time

from example.app.models import SimpleObject, RelatableObject, RelationsTestObject, Tag, DumbTag


def test_simple_result():
    hit = {
        "_source": {
            "id": 123,
            "name": "test",
            "simple_id": 2,
            "nested": {
                "id": 4,
                "denormalized_datums": "what"
            }
        }
    }
    test = RelatableObject.search_objects.from_es(hit)
    assert test.id == 123
    assert isinstance(test, RelatableObject)

    hit = {
        "_source": {
            "id": 123,
            "name": "test",
            "simple_id": None,
            "nested": None
        }
    }
    test = RelatableObject.search_objects.from_es(hit)
    assert test.id == 123
    assert isinstance(test, RelatableObject)


@pytest.mark.django_db
def test_simple_get(es_client):

    management.call_command("sync_es")

    test_object = mommy.make(SimpleObject)
    test_object.index()
    time.sleep(1)  # Let the index refresh

    from_es = SimpleObject.search_objects.get(id=test_object.id)
    assert from_es.foo == test_object.foo
    assert from_es.bar == test_object.bar
    assert from_es.baz == test_object.baz
    assert from_es.__class__.__name__ == "SimpleObject_ElasticSearchResult"
    assert from_es.save is None

    from_es = SimpleObject.search_objects.get(pk=test_object.id)
    assert from_es.foo == test_object.foo

    with pytest.raises(RelatableObject.DoesNotExist):
        RelatableObject.search_objects.get(id=test_object.id)

    with pytest.raises(RelatableObject.DoesNotExist):
        RelatableObject.search_objects.get()


@pytest.mark.django_db
def test_related_get(es_client):

    management.call_command("sync_es")

    test_object = mommy.make(RelatableObject)

    from_es = RelatableObject.search_objects.get(id=test_object.id)
    assert from_es.__class__.__name__ == "RelatableObject_ElasticSearchResult"
    assert from_es.save is None
    assert from_es.name == test_object.name
    assert from_es.nested.id == test_object.nested.id
    assert hasattr(from_es, "nested_id") is False
    assert from_es.simple_id == test_object.simple_id
    assert from_es.simple.id == test_object.simple.id


@pytest.mark.django_db
def test_m2m(es_client):

    management.call_command("sync_es")

    tags = mommy.make(Tag, _quantity=3)
    dumb_tags = mommy.make(DumbTag, _quantity=2)

    test_object = mommy.make(RelationsTestObject, make_m2m=False)
    test_object.tags.add(*tags)
    test_object.dumb_tags.add(*dumb_tags)
    test_object.index()  # Reindex now that we've added tags...

    from_es = RelationsTestObject.search_objects.get(id=test_object.id)
    assert from_es.__class__.__name__ == "RelationsTestObject_ElasticSearchResult"
    assert from_es.save is None
    assert from_es.data == test_object.data
    assert from_es.tags.count() == 3

    for i in range(0, 3):
        assert from_es.tags.all()[i].id == tags[i].id

    assert dumb_tags[0].id in from_es.dumb_tags.values_list("pk", flat=True)
    assert dumb_tags[1].id in from_es.dumb_tags.values_list("pk", flat=True)
