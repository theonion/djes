import pytest
from example.app.models import *  # noqa
from model_mommy import mommy
from django.utils import timezone


@pytest.mark.django_db
def test_simple(es_client):
    now = timezone.now()

    test = SimpleObject.objects.create(
        foo=1,
        bar="Bar",
        baz="baz",
        published=now
    )
    assert test.to_dict() == {
        "id": test.id,
        "foo": 1,
        "bar": "Bar",
        "baz": "baz",
        "published": now
    }


@pytest.mark.django_db
def test_custom_field(es_client):
    test = CustomFieldObject.objects.create(
        color="#008E50"
    )
    assert test.to_dict() == {
        "id": test.id,
        "color": {
            "red": "00",
            "green": "8E",
            "blue": "50"
        }
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
    dumb_tags = mommy.make(DumbTag, _quantity=4)

    test_object = mommy.make(RelationsTestObject, make_m2m=False)
    test_object.tags.add(*tags)
    test_object.dumb_tags.add(*dumb_tags)

    document = test_object.to_dict()

    assert document["id"] == test_object.id
    assert document["data"] == test_object.data

    assert len(document["tags"]) == 3
    assert {"id": tags[0].id, "name": tags[0].name} in document["tags"]

    # Not for now...
    # assert len(document["dumb_tags"]) == 4
    # assert dumb_tags[0].id in document["dumb_tags"]
