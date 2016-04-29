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
def test_poly_reference(es_client):
    child_a = PolyChildA.objects.create(slug='slug', number=1)
    child_b = PolyChildB.objects.create(album='st.anger', band_name='metallica')
    parent_a = PolyParent.objects.get(id=child_a.id)
    parent_b = PolyParent.objects.get(id=child_b.id)

    poly_relationship_a = PolyRelationship.objects.create(poly_parent=parent_a)
    assert poly_relationship_a.to_dict() == {
        'poly_parent': {
            'text': '',
            'slug': 'slug',
            'number': 1,
            'polyparent_ptr_id': 1,
            'id': 1
        },
        'id': 1
    }

    poly_relationship_b = PolyRelationship.objects.create(poly_parent=parent_b)
    assert poly_relationship_b.to_dict() == {
        'poly_parent': {
            'album': 'st.anger',
            'text': '',
            'band_name': 'metallica',
            'id': 2,
            'polyparent_ptr_id': 2
        },
        'id': 2
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


@pytest.mark.django_db
def test_save_index():

    content = SimpleObject.objects.create(foo=1)

    # Added to index on create
    SimpleObject.search_objects.refresh()
    assert 1 == SimpleObject.search_objects.search().count()

    # Remove From Index
    content.save(index=False)
    SimpleObject.search_objects.refresh()
    assert 0 == SimpleObject.search_objects.search().count()

    # Re-insert into index
    content.save(index=True)
    SimpleObject.search_objects.refresh()
    assert 1 == SimpleObject.search_objects.search().count()
