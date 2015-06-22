from django.apps import apps
from django.core import management
from django.db.backends import utils
from django.utils import timezone

from model_mommy import mommy
import pytest
import time

from djes.factory import shallow_class_factory

from example.app.models import (
    SimpleObject, RelatableObject, RelationsTestObject, RelatedNestedObject,
    Tag, DumbTag, ReverseRelationsParentObject, ReverseRelationsChildObject
)


def test_shallow_factory():

    shallow_class = shallow_class_factory(SimpleObject)
    assert issubclass(shallow_class, SimpleObject)

    name = "{}_ElasticSearchResult".format(SimpleObject.__name__)
    name = utils.truncate_name(name, 80, 32)
    # try to get the model from the django registry
    cached_shallow_class = apps.get_model(SimpleObject._meta.app_label, name)
    assert cached_shallow_class == shallow_class


def test_simple_result():
    now = timezone.now()
    hit = {
        "_source": {
            "id": 1,
            "foo": 33,
            "bar": "Thirty Three",
            "baz": "thirty-three",
            "published": now.isoformat()
        }
    }
    test = SimpleObject.search_objects.from_es(hit)
    assert test.id == 1
    assert isinstance(test, SimpleObject)
    assert test.published == now


def test_related_result():
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
    assert isinstance(test.nested, RelatedNestedObject)
    assert isinstance(test, RelatableObject)

    hit = {
        "_source": {
            "id": 123,
            "name": "test",
            "simple_id": None,
        }
    }
    test = RelatableObject.search_objects.from_es(hit)
    assert test.id == 123
    assert test.nested is None
    assert isinstance(test, RelatableObject)


def test_reverse_relation_result():
    hit = {
        "_source": {
            "id": 123,
            "name": "test",
            "children": [{
                "id": 4,
                "name": "what"
            },{
                "id": 5,
                "name": "who"
            }]
        }
    }
    test = ReverseRelationsParentObject.search_objects.from_es(hit)
    assert test.id == 123
    assert test.children.count() == 2
    assert len(test.children.all()) == 2
    assert isinstance(test.children.all()[0], ReverseRelationsChildObject)


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
def test_simple_delete(es_client):

    management.call_command("sync_es")

    test_object = mommy.make(SimpleObject)
    test_object.index()
    time.sleep(1)

    from_es = SimpleObject.search_objects.get(pk=test_object.id)
    assert from_es.foo == test_object.foo

    test_object.delete_index()
    with pytest.raises(SimpleObject.DoesNotExist):
        SimpleObject.search_objects.get(pk=test_object.pk)


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



