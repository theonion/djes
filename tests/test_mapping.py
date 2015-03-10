from example.app.models import SimpleObject, ManualMappingObject, RelatableObject


def test_simple():
    mapping = SimpleObject.search_objects.get_mapping()
    assert mapping.doc_type == "app_simpleobject"
    assert mapping.to_dict() == {
        "app_simpleobject": {
            "_id": {
                "path": "id"
            },
            "properties": {
                "foo": {"type": "long"},
                "id": {"type": "long"},
                "bar": {"type": "string"},
                "baz": {"index": "not_analyzed", "type": "string"}
            }
        }
    }


def test_manual():
    mapping = ManualMappingObject.search_objects.get_mapping()
    assert mapping.doc_type == "super_manual_mapping"
    assert mapping.to_dict() == {
        "super_manual_mapping": {
            "_id": {
                "path": "simpleobject_ptr"
            },
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
    mapping = RelatableObject.search_objects.get_mapping()
    assert mapping.to_dict() == {
        "app_relatableobject": {
            "_id": {
                "path": "id"
            },
            "properties": {
                "id": {"type": "long"},
                "name": {"type": "string"},
                "simple_id": {"type": "long"},
                "nested": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "long"},
                        "denormalized_datums": {"type": "string"}
                    }
                },
            }
        }
    }
