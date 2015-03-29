from djes.apps import indexable_registry

from example.app.models import SimpleObject, ManualMappingObject


def test_simple():
    assert indexable_registry.all_models.get("app_simpleobject") == SimpleObject
    assert len(indexable_registry.all_models) == 7


def test_base():
    assert SimpleObject.get_base_class() == SimpleObject
    assert ManualMappingObject.get_base_class() == SimpleObject
