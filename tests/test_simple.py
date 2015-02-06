from example.app.models import SimpleObject


def test_simple():
    assert True

    test = SimpleObject(foo=3)
    assert test.foo == 3

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

    