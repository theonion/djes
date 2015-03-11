import time

from djes.management.commands.sync_es import get_indexes, sync_index
from elasticsearch_dsl.connections import connections


def test_index_settings():
	indexes = get_indexes()
	assert indexes["djes-example"]["settings"] == {"index": {"number_of_replicas": "1"}}

def test_sync_index():
	# Some setup code
	es = connections.get_connection("default")
	es.indices.delete("djes-testing-index", ignore=[404])
	es.indices.delete("djes-testing-index_0001", ignore=[404])
	es.indices.delete("djes-testing-index_0002", ignore=[404])

	settings_body = {
		"settings": {"index": {"number_of_replicas": "1"}},
		"mappings": {
			"testing": {
				"properties": {
					"foo": {"type": "string"}
				}
			}
		}
	}
	sync_index("djes-testing-index", body=settings_body)

	assert es.indices.exists("djes-testing-index_0001")
	assert es.indices.get_alias("djes-testing-index") == {"djes-testing-index_0001": {"aliases": {"djes-testing-index": {}}}}

	# Let's sync again, this should update the settings
	settings_body["settings"]["index"]["number_of_replicas"] = "2"
	sync_index("djes-testing-index", body=settings_body)
	assert es.indices.exists("djes-testing-index_0001")
	assert es.indices.exists("djes-testing-index_0002") is False

	# Make sure the settings took
	new_settings = es.indices.get_settings("djes-testing-index_0001")["djes-testing-index_0001"]["settings"]
	assert new_settings["index"]["number_of_replicas"] == "2"

	# Now let's add another mapping
	settings_body["mappings"]["testing-two"] = {
		"properties": {
			"bar": {"type": "integer"}
		}
	}
	sync_index("djes-testing-index", body=settings_body)

	# Make sure the new mapping got added
	assert es.indices.exists("djes-testing-index_0001")
	assert es.indices.exists("djes-testing-index_0002") is False
	new_mapping = es.indices.get_mapping(index="djes-testing-index", doc_type="testing-two")["djes-testing-index_0001"]
	assert new_mapping["mappings"]["testing-two"] == settings_body["mappings"]["testing-two"]

	# Now lets add another field to that mapping
	settings_body["mappings"]["testing-two"] = {
		"properties": {
			"bar": {"type": "integer"},
			"baz": {"type": "string"}
		}
	}
	sync_index("djes-testing-index", body=settings_body)
	assert es.indices.exists("djes-testing-index_0001")
	assert es.indices.exists("djes-testing-index_0002") is False
	new_mapping = es.indices.get_mapping(index="djes-testing-index", doc_type="testing-two")["djes-testing-index_0001"]
	assert new_mapping["mappings"]["testing-two"] == settings_body["mappings"]["testing-two"]

	# Now let's add a mapping that will error out
	settings_body["mappings"]["testing-two"] = {
		"properties": {
			"bar": {"type": "integer"},
			"baz": {"type": "long"}
		}
	}
	sync_index("djes-testing-index", body=settings_body)

	assert es.indices.exists("djes-testing-index_0001")
	assert es.indices.exists("djes-testing-index_0002")
	new_mapping = es.indices.get_mapping(index="djes-testing-index", doc_type="testing-two")["djes-testing-index_0002"]
	assert new_mapping["mappings"]["testing-two"] == settings_body["mappings"]["testing-two"]

	# Some teardown code
	es.indices.delete("djes-testing-index", ignore=[404])
	es.indices.delete("djes-testing-index_0001", ignore=[404])
	es.indices.delete("djes-testing-index_0002", ignore=[404])
