# DJES Change Log

## Development

## Version 0.1.110

- `shallow_class_factory` defines a generic Mapping wrapper for `_ElasticSearchResult` objects.

## Version 0.1.109

- `Indexable.save` calls `delete_index` when `index=False` (mirrors `index()` behavior).
- Added python 3.5 testing support

## Version 0.1.108

- Bump `elasticsearch_dsl` 0.0.4 -> 0.0.9
- Tests support alternate elasticsearch host via `ELASTICSEARCH_HOST` environment variable
