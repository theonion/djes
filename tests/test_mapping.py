from example.app.models import (
    SimpleObject, ManualMappingObject, RelatableObject,
    RelationsTestObject)


def test_simple():
    assert SimpleObject.mapping.doc_type == "app_simpleobject"
    assert SimpleObject.mapping.to_dict() == {
        "app_simpleobject": {
            "_id": {
                "path": "id"
            },
            "dynamic": "strict",
            "properties": {
                "foo": {"type": "long"},
                "id": {"type": "long"},
                "bar": {"type": "string"},
                "baz": {"index": "not_analyzed", "type": "string"}
            }
        }
    }


def test_manual():
    assert ManualMappingObject.mapping.doc_type == "super_manual_mapping"
    assert ManualMappingObject.mapping.to_dict() == {
        "super_manual_mapping": {
            "_id": {
                "path": "simpleobject_ptr"
            },
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
                "simpleobject_ptr_id": {"type": "long"},
            }
        }
    }


def test_related():
    assert RelatableObject.mapping.to_dict() == {
        "app_relatableobject": {
            "_id": {
                "path": "id"
            },
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
    assert RelationsTestObject.mapping.to_dict() == {
        "app_relationstestobject": {
            "_id": {
                "path": "id"
            },
            "dynamic": "strict",
            "properties": {
                "id": {"type": "long"},
                "data": {"type": "string"},
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
