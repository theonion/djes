import logging

from elasticsearch_dsl.connections import connections

from django.test import TestCase
from djes.management.commands.sync_es import get_indexes, sync_index


class BaseIndexableTestCase(TestCase):
    """A TestCase which handles setup and teardown of elasticsearch indexes."""

    elasticsearchLogger = logging.getLogger('elasticsearch')

    def setUp(self):
        """ If you're reading this. I am gone and dead, presumably.
            Elasticsearch's logging is quite loud and lets us know
            about anticipated errors, so I set the level to ERROR only.
            If elasticsearch is giving you trouble in tests and you
            aren't seeing any info, get rid of this. God bless you.
        """
        self.elasticsearchLogger.setLevel(logging.ERROR)
        self.es = connections.get_connection("default")
        self.indexes = get_indexes()

        for index in list(self.indexes):
            self.es.indices.delete_alias("{}*".format(index), "_all", ignore=[404])
            self.es.indices.delete("{}*".format(index), ignore=[404])

        for index, body in self.indexes.items():
            sync_index(index, body)

    def tearDown(self):
        for index in list(self.indexes):
            self.es.indices.delete_alias("{}*".format(index), "_all", ignore=[404])
            self.es.indices.delete("{}*".format(index), ignore=[404])
