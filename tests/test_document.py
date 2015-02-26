import pytest
from example.app.models import SimpleObject


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
