import pytest

from django.core import management

from elasticsearch_dsl import filter as es_filter
from model_mommy import mommy

from djes.search import SearchParty
from example.app.models import SimpleObject, ManualMappingObject, Tag


@pytest.mark.django_db
def test_simple_search(es_client):
    management.call_command("sync_es")

    mommy.make(SimpleObject, _quantity=10)
    mommy.make(ManualMappingObject, _quantity=5)
    SimpleObject.search_objects.refresh()

    results = SimpleObject.search_objects.search()
    assert results.count() == 15
    assert len(results) == 15
    assert isinstance(results[0], SimpleObject)

    assert len(results[:3]) == 3
    assert len(results[1:4]) == 3
    assert len(results[:20]) == 15

    results = ManualMappingObject.search_objects.search()
    assert results.count() == 5
    assert len(results) == 5
    assert isinstance(results[0], ManualMappingObject)

    es_obj = ManualMappingObject.search_objects.search()[0]
    db_obj = ManualMappingObject.objects.get(id=es_obj.id)
    assert es_obj.id == db_obj.id
    assert es_obj.qux == db_obj.qux
    assert es_obj.garbage is None  # This one isn't indexed...


@pytest.mark.django_db
def test_tag_search(es_client):
    management.call_command("sync_es")

    mommy.make(Tag, _quantity=10)
    Tag.search_objects.refresh()

    tag_results = Tag.search_objects.search()
    assert tag_results.count() == 10
    assert len(tag_results) == 10
    assert isinstance(tag_results[0], Tag)


@pytest.mark.django_db
def test_full_search(es_client):
    management.call_command("sync_es")

    mommy.make(SimpleObject, _quantity=10)
    mommy.make(ManualMappingObject, _quantity=5)
    SimpleObject.search_objects.refresh()

    assert SimpleObject.search_objects.search().full().count() == 15
    assert len(SimpleObject.search_objects.search().full()) == 15
    assert ManualMappingObject.search_objects.search().full().count() == 5
    assert len(ManualMappingObject.search_objects.search().full()) == 5

    assert len(SimpleObject.search_objects.search().full()[:3]) == 3
    assert len(SimpleObject.search_objects.search().full()[:20]) == 15

    es_obj = ManualMappingObject.search_objects.search().full()[0]
    db_obj = ManualMappingObject.objects.get(id=es_obj.id)
    assert es_obj.id == db_obj.id
    assert es_obj.qux == db_obj.qux
    assert es_obj.garbage == db_obj.garbage  # This one isn't indexed, but this is a full search

    for obj in SimpleObject.search_objects.search().full():
        assert isinstance(obj, SimpleObject)


@pytest.mark.django_db
def test_search_party(es_client):
    management.call_command("sync_es")

    mommy.make(SimpleObject, baz="tired", _quantity=5)
    mommy.make(SimpleObject, baz="awake", _quantity=5)
    SimpleObject.search_objects.refresh()

    tired_es = SimpleObject.search_objects.search().filter(
        es_filter.Term(baz="tired")
    ).sort(
        "id"
    )
    awake_es = SimpleObject.search_objects.search().filter(
        es_filter.Term(baz="awake")
    ).sort(
        "id"
    )
    assert tired_es.count() == 5
    assert awake_es.count() == 5

    search_party = SearchParty()
    search_party.register_search(tired_es, primary=True)
    search_party.register_search(awake_es, search_range=(0, 1))

    import pdb; pdb.set_trace()
