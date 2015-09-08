from djes.management.commands.sync_es import get_indexes, sync_index


def test_index_settings():
    indexes = get_indexes()
    assert indexes["djes-example"]["settings"]["index"]["number_of_replicas"] == 1


def test_sync_index(es_client):
    # Some setup code
    es_client.indices.delete_alias("djes-testing-index_*", "_all", ignore=[404])
    es_client.indices.delete("djes-testing-index_*", ignore=[404])

    settings_body = {
        "settings": {
            "index": {
                "number_of_replicas": "1",

                "analysis": {
                    "analyzer": {
                        "autocomplete": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "char_filter":  ["html_strip"],
                            "filter": ["lowercase", "stop", "snowball"]
                        }
                    }
                }
            },
        },
        "mappings": {
            "testing": {
                "properties": {
                    "foo": {"type": "string"}
                }
            }
        }
    }
    sync_index("djes-testing-index", body=settings_body)

    assert es_client.indices.exists("djes-testing-index_0001")
    assert es_client.indices.get_alias("djes-testing-index") == {
        "djes-testing-index_0001": {
            "aliases": {"djes-testing-index": {}}
        }
    }

    # Let's sync again, this should update the settings
    settings_body["settings"]["index"]["number_of_replicas"] = "2"
    sync_index("djes-testing-index", body=settings_body)
    assert es_client.indices.exists("djes-testing-index_0001")
    assert es_client.indices.exists("djes-testing-index_0002") is False

    # Make sure the settings took
    new_settings = es_client.indices.get_settings("djes-testing-index_0001")
    new_settings = new_settings["djes-testing-index_0001"]["settings"]
    assert new_settings["index"]["number_of_replicas"] == "2"

    # Now let's add another mapping
    settings_body["mappings"]["testing-two"] = {
        "properties": {
            "bar": {"type": "integer"}
        }
    }
    sync_index("djes-testing-index", body=settings_body)

    # Make sure the new mapping got added
    assert es_client.indices.exists("djes-testing-index_0001")
    assert es_client.indices.exists("djes-testing-index_0002") is False
    new_mapping = es_client.indices.get_mapping(index="djes-testing-index", doc_type="testing-two")
    new_mapping = new_mapping["djes-testing-index_0001"]
    assert new_mapping["mappings"]["testing-two"] == settings_body["mappings"]["testing-two"]

    # Now lets add another field to that mapping
    settings_body["mappings"]["testing-two"] = {
        "properties": {
            "bar": {"type": "integer"},
            "baz": {"type": "string"}
        }
    }
    sync_index("djes-testing-index", body=settings_body)
    assert es_client.indices.exists("djes-testing-index_0001")
    assert es_client.indices.exists("djes-testing-index_0002") is False
    new_mapping = es_client.indices.get_mapping(index="djes-testing-index", doc_type="testing-two")
    new_mapping = new_mapping["djes-testing-index_0001"]
    assert new_mapping["mappings"]["testing-two"] == settings_body["mappings"]["testing-two"]

    # Now let's add a mapping that will error out
    settings_body["mappings"]["testing-two"] = {
        "properties": {
            "bar": {"type": "integer"},
            "baz": {"type": "long"}
        }
    }
    sync_index("djes-testing-index", body=settings_body)

    assert es_client.indices.exists("djes-testing-index_0001")
    assert es_client.indices.exists("djes-testing-index_0002")
    new_mapping = es_client.indices.get_mapping(index="djes-testing-index", doc_type="testing-two")
    new_mapping = new_mapping["djes-testing-index_0002"]
    assert new_mapping["mappings"]["testing-two"] == settings_body["mappings"]["testing-two"]

    # Add another mapping
    settings_body["mappings"]["testing-two"] = {
        "properties": {
            "foo": {"type": "long"},
            "baz": {"type": "integer"}
        }
    }
    sync_index("djes-testing-index", body=settings_body)
    assert es_client.indices.exists("djes-testing-index_0001")
    assert es_client.indices.exists("djes-testing-index_0002")
    assert es_client.indices.exists("djes-testing-index_0003")

    es_client.indices.delete_alias("djes-testing-index_*", "_all", ignore=[404])
    es_client.indices.delete("djes-testing-index_*", ignore=[404])
