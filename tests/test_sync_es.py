from djes.management.commands.sync_es import get_indexes

def test_index_settings():
	indexes = get_indexes()
	assert indexes["djes-example"]["settings"] == {"number_of_replicas": 2}


	assert "butts" in indexes