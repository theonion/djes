import pytest
from example.app.models import (
    SimpleObject, RelatableObject, RelatedSimpleObject, RelatedNestedObject
)


@pytest.mark.django_db
def test_simple():
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
def test_relatable():
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
