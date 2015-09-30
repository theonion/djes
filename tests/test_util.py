from django.db import connection, reset_queries
from django.conf import settings
import pytest
from model_mommy import mommy

from djes.util import batched_queryset
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
            chunks = list(batched_queryset(SimpleObject.objects.all(), chunksize=chunksize))
            assert objects == chunks
            assert len(connection.queries) == expected_queries
    finally:
        settings.DEBUG = False
