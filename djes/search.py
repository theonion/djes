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


class SearchParty(object):
    """
    Generator for multiple searches that allows for searches to iterate through the results of
    multiple queries, while providing explicit logic for indexing.
    """
    def __init__(self, *args, **kwargs):
        self.results = []
        self.searches = {}
        self.primary_search = None

    def __getitem__(self, n):
        if n + 1 <= len(self.results):
            return self.results[n]
        elif n - len(self.results) > 1:
            for i in range(len(self.results), n):
                self[i]
        search = self.get_search(n)
        self.results.append(self.get_result(search))
        return self.results[n]

    def get_search(self, n):
        for search, config in self.searches.items():
            search_ranges = config.get("ranges")
            if search_ranges:
                for search_range in search_ranges:
                    if not search_range:
                        continue
                    elif n >= search_range[0] and n < search_range[1]:
                        return search
        return self.primary_search

    def get_result(self, search):
        count = self.searches[search]["count"]
        result = search[count]
        self.searches[search]["count"] += 1
        return result

    def register_search(self, search, search_range=None, primary=False):
        if primary or self.primary_search is None:
            self.primary_search = search
            self.searches[search] = {"ranges": None, "count": 0}
        else:
            if type(search_range) is list:
                for srange in search_range:
                    self.validate_range(srange)
            else:
                self.validate_range(search_range)
                search_range = [search_range]
            self.searches[search] = {"ranges": search_range, "count": 0}

    def validate_range(self, search_range):
        if search_range is None:
            raise ValueError("Received a None value for search range.")
        if type(search_range) is not tuple:
            raise TypeError(
                "{}. Search ranges must be formatted as a tuple. e.g., (x, y).".format(
                    search_range
                )
            )
        if len(search_range) != 2:
            raise IndexError(
                "{}. Search ranges must be 2 values. e.g., (x, y).".format(search_range)
            )
        if search_range[0] > search_range[1]:
            raise ValueError(
                ("{}. The first value of a search range must be less than the")
                ("following value.").format(search_range)
            )
