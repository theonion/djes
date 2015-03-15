import pytest
from example.app.models import (
    SimpleObject, RelatableObject, RelatedSimpleObject, RelatedNestedObject,
    Tag, RelationsTestObject
)
from model_mommy import mommy


@pytest.mark.django_db
def test_simple(es_client):
    test = SimpleObject.objects.create(
        foo=1,
        bar="Bar",
        baz="baz"
    )
    assert test.to_dict() == {
        "id": test.id,
        "foo": 1,
        "bar": "Bar",
        "baz": "baz"
    }


@pytest.mark.django_db
def test_relatable(es_client):
    simple = RelatedSimpleObject.objects.create(datums="Some datums")
    nested = RelatedNestedObject.objects.create(denormalized_datums="Some denormalized datums")

    test = RelatableObject.objects.create(
        name="testing",
        simple=simple,
        nested=nested
    )
    assert test.to_dict() == {
        "id": test.id,
        "name": "testing",
        "simple_id": simple.id,
        "nested": {
            "id": nested.id,
            "denormalized_datums": "Some denormalized datums"
        }
    }


@pytest.mark.django_db
def test_many_to_many(es_client):

    tags = mommy.make(Tag, _quantity=3)

    test_object = mommy.make(RelationsTestObject, make_m2m=False)
    test_object.tags.add(*tags)

    document = test_object.to_dict()

    assert document["id"] == test_object.id
    assert document["data"] == test_object.data

    assert len(document["tags"]) == 3
    assert {"id": tags[0].id, "name": tags[0].name} in document["tags"]
