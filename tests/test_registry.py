from djes.apps import indexable_registry

from example.app.models import SimpleObject


def test_simple():
    assert indexable_registry.all_models == {"app_simpleobject": SimpleObject}
