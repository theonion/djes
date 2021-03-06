from djes.mapping import get_first_mapping
from example.app.models import (
    SimpleObject, ManualMappingObject, RelatableObject,
    RelationsTestObject, CustomFieldObject, ChildObject,
    GrandchildObject, ReverseRelationsParentObject)


def test_simple():
    assert SimpleObject.search_objects.mapping.doc_type == "app_simpleobject"
    assert SimpleObject().mapping.doc_type == "app_simpleobject"
    assert SimpleObject.search_objects.mapping.to_dict() == {
        "app_simpleobject": {
            "dynamic": "strict",
            "properties": {
                "foo": {"type": "long"},
                "id": {"type": "long"},
                "bar": {"type": "string"},
                "baz": {"index": "not_analyzed", "type": "string"},
                "published": {"type": "date"}
            }
        }
    }


def test_manual():
    assert ManualMappingObject.search_objects.mapping.doc_type == "super_manual_mapping"
    assert {
        "super_manual_mapping": {
            "dynamic": "strict",
            "properties": {
                "foo": {"type": "long"},
                "id": {"type": "long"},
                "bar": {
                    "type": "string",
                    "fields": {
                        "raw": {"type": "string", "index": "not_analyzed"}
                    }
                },
                "baz": {"index": "not_analyzed", "type": "string"},
                "qux": {"type": "string"},
                "status": {"index": "not_analyzed", "type": "string"},
                "simpleobject_ptr_id": {"type": "long"},
                "published": {"type": "date"}
            }
        }
    } == ManualMappingObject.search_objects.mapping.to_dict()


def test_custom():
    assert CustomFieldObject.search_objects.mapping.to_dict() == {
        "app_customfieldobject": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "long"},
                "color": {
                    "type": "object",
                    "properties": {
                        "red": {"type": "string"},
                        "green": {"type": "string"},
                        "blue": {"type": "string"}
                    }
                },
            }
        }
    }


def test_inheritance():

    assert get_first_mapping(SimpleObject) is None
    assert get_first_mapping(ChildObject) == ChildObject.Mapping
    assert get_first_mapping(GrandchildObject) == ChildObject.Mapping


def test_related():
    assert RelatableObject.search_objects.mapping.to_dict() == {
        "app_relatableobject": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "long"},
                "name": {"type": "string"},
                "simple_id": {"type": "long"},
                "nested": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "long"},
                        "denormalized_datums": {"type": "string"}
                    }
                },
            }
        }
    }


def test_many_to_many():
    assert RelationsTestObject.search_objects.mapping.to_dict() == {
        "app_relationstestobject": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "long"},
                "data": {"type": "string"},
                "dumb_tags": {"type": "long"},
                "tags": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "long"},
                        "name": {"type": "string"}
                    }
                }
            }
        }
    }


def test_reverse_relations():
    assert ReverseRelationsParentObject.search_objects.mapping.to_dict() == {
        "app_reverserelationsparentobject": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "long"},
                "name": {"type": "string"},
                "children": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "long"},
                        "name": {"type": "string"}
                    }
                }
            }
        }
    }


def test_get_doc_types():
    assert SimpleObject.get_doc_types() == [
        'app_simpleobject',
        'super_manual_mapping',
        'app_childobject',
        'app_grandchildobject'
    ]
