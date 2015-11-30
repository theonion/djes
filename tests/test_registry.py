from djes.apps import indexable_registry

from example.app.models import (
    SimpleObject, ManualMappingObject, ChildObject, GrandchildObject, PolyOrphan
)


def test_simple():
    assert indexable_registry.all_models.get("app_simpleobject") == SimpleObject
    assert len(indexable_registry.all_models) == 17


def test_base():
    assert SimpleObject.get_base_class() == SimpleObject
    assert ManualMappingObject.get_base_class() == SimpleObject
    assert ChildObject.get_base_class() == SimpleObject
    assert GrandchildObject.get_base_class() == SimpleObject


def test_orphan():
    assert PolyOrphan.is_orphaned()
    assert PolyOrphan.get_base_class() == PolyOrphan
