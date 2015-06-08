from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.result import Response
from elasticsearch_dsl import Search

from .apps import indexable_registry


class ShallowResponse(Response):
    def count(self):
        return self.hits.total

    def __len__(self):
        return self.hits.total


class FullResponse(Response):

    def count(self):
        return self.hits.total

    def __len__(self):
        if 'size' in self._extra:
            return min(self._extra['size'], self.hits.total)
        return self.hits.total

    def _get_result(self, hit):
        doc_type = hit['_type']
        _id = int(hit["_id"])
        return self._in_bulk[doc_type][_id]

    @property
    def hits(self):
        if not hasattr(self, "_hits"):
            # If this is the first call, we need to cache all the hits with bulk queries
            hits = self._d_["hits"]["hits"]

            doc_type_map = {}
            for hit in hits:
                doc_type = hit["_type"]
                if doc_type not in doc_type_map:
                    doc_type_map[doc_type] = []
                doc_type_map[doc_type].append(int(hit["_id"]))

            self._in_bulk = {}
            for doc_type, ids in doc_type_map.items():
                cls = indexable_registry.all_models[doc_type]
                self._in_bulk[doc_type] = cls.objects.in_bulk(ids)

        return super(FullResponse, self).hits


class LazySearch(Search):
    """This extends the base Search object, allowing for Django-like lazy execution"""

    def __len__(self):
        if 'size' in self._extra:
            return min(self._extra['size'], self.count())
        return self.count()

    def __getitem__(self, n):
        if isinstance(n, int):
            return self.execute()[n]

        if not isinstance(n, slice):
            raise TypeError("List indices must be integers")

        return super(LazySearch, self).__getitem__(n)

    def full(self):
        s = self._clone()
        s._full = True
        s._fields = ["_id"]
        return s

    def _clone(self):
        s = super(LazySearch, self)._clone()
        s._full = getattr(self, "_full", False)
        return s

    def execute(self):
        """
        Execute the search and return an instance of ``Response`` wrapping all
        the data.
        """
        if hasattr(self, "_executed"):
            return self._executed

        es = connections.get_connection(self._using)

        if getattr(self, "_full", False) is False:
            self._executed = ShallowResponse(es.search(index=self._index,
                                                   doc_type=self._doc_type,
                                                   body=self.to_dict(),
                                                   **self._params),
                                         callbacks=self._doc_type_map)
        else:
            self._executed = FullResponse(es.search(index=self._index,
                                                doc_type=self._doc_type,
                                                body=self.to_dict(),
                                                **self._params))

        return self._executed
