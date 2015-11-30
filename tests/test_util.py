from django.db import connection, reset_queries
from django.conf import settings

import pytest
from model_mommy import mommy
from elasticsearch_dsl.connections import connections

from djes.utils.query import batched_queryset
from example.app.models import SimpleObject


@pytest.mark.django_db
def test_empty_queryset(es_client):
    assert list(batched_queryset(SimpleObject.objects.all())) == []


@pytest.mark.django_db
def test_various_chunk_sizes(es_client):
    objects = mommy.make(SimpleObject, _quantity=10)
    for size in range(1, 12):
        assert objects == list(batched_queryset(SimpleObject.objects.all(), chunksize=size))


@pytest.mark.django_db
def test_count_batch_queries(es_client):
    objects = mommy.make(SimpleObject, _quantity=10)

    try:
        settings.DEBUG = True  # Must be TRUE to track connection queries

        # 1 query to get initial primary key, plus 1 per batch
        for chunksize, expected_queries in [(10, 2),
                                            (5, 3),
                                            (3, 5)]:
            reset_queries()
            results = list(batched_queryset(SimpleObject.objects.all(), chunksize=chunksize))
            assert objects == results
            assert len(connection.queries) == expected_queries
    finally:
        settings.DEBUG = False


@pytest.mark.django_db
def test_delete_during_query(es_client):
    objects = mommy.make(SimpleObject, _quantity=10)
    qs = batched_queryset(SimpleObject.objects.all(), chunksize=3)
    results = [next(qs) for _ in range(3)]
    # Delete during batched fetch
    objects[3].delete()  # Not yet fetched
    # Finish batched fetch
    results.extend(list(qs))
    # Querys
    assert results == (objects[:3] + objects[4:])


@pytest.mark.django_db
def test_create_during_query(es_client):
    objects = mommy.make(SimpleObject, _quantity=10)
    qs = batched_queryset(SimpleObject.objects.all(), chunksize=3)
    results = [next(qs) for _ in range(3)]
    # Create more objects during batched fetch
    new_objects = mommy.make(SimpleObject, _quantity=10)
    # Finish batched fetch
    results.extend(list(qs))

    # Final chunk (based on initial object count 10) would normally be size 1. Number of chunks
    # fetched is based on initial size, but last chunk fetched will grab enough new objects to fill
    # chunk (size 3).
    assert results == (objects + new_objects[:2])


@pytest.mark.django_db
def test_delete_object_es(es_client):
    es = connections.get_connection('default')
    obj = mommy.make(SimpleObject)

    SimpleObject.search_objects.refresh()

    index = SimpleObject.search_objects.mapping.index
    doc_type = SimpleObject.search_objects.mapping.doc_type
    obj_id_query = {
        "query": {
            "ids": {
                "values": [obj.id]
            }
        }
    }
    results = es.search(index=index, doc_type=doc_type, body=obj_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 1

    obj.delete()

    SimpleObject.search_objects.refresh()

    results = es.search(index=index, doc_type=doc_type, body=obj_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 0


@pytest.mark.django_db
def test_delete_non_indexed_object(es_client):
    es = connections.get_connection('default')
    obj = mommy.make(SimpleObject)

    SimpleObject.search_objects.refresh()

    index = SimpleObject.search_objects.mapping.index
    doc_type = SimpleObject.search_objects.mapping.doc_type
    obj_id_query = {
        "query": {
            "ids": {
                "values": [obj.id]
            }
        }
    }
    results = es.search(index=index, doc_type=doc_type, body=obj_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 1

    # remove it from the index
    obj.delete_index()

    SimpleObject.search_objects.refresh()

    results = es.search(index=index, doc_type=doc_type, body=obj_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 0

    # call delete and verify errors aren't thrown
    obj.delete()
