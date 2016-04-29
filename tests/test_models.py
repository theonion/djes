import pytest

from example.app.models import SimpleObject


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
