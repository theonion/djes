Quickstart
==========

Requirements
------------

`djes` requires:

  - Django >= 1.8
  - elasticsearch-dsl-py >= 0.0.4
  - Python 2.7, 3.3 or 3.4

Installation
------------

You can install `djes` from PyPi:

    $ pip install djes

Next, just add `djes` to your `INSTALLED_APPS`:

    INSTALLED_APPS += (
        'djes',
    )

By default, `djes` uses `localhost:9200` as the location of your Elasticsearch server, but this can be customized using the `ES_CONNECTIONS` settings attribute.

    ES_CONNECTIONS = {
        "default": {
            "hosts": "192.168.1.143:9200"
        }
    }

Making Your Models Indexable
----------------------------

In order to make a model Indexable, just extend from `Indexable`, instead of Django's `model.Model`, like so:

    from djes.models import Indexable

    class SimpleObject(Indexable):
        foo = models.IntegerField()

Syncing Your Mappings
--------------------

Now that youve setup some models, save the mappings to Elasticsearch, using the mangement command `sync_es`:

    python manage.py sync_es

Searching
---------

In order to use Elasticsearch, instead of your database, just use the `search_objects` manager, like so:

    >>> SimpleObject.objects.create(foo=666)
    <SimpleObject: SimpleObject object>
    >>> SimpleObject.search_objects.search().filter('term', foo=666).count()
    1
    >>> SimpleObject.search_objects.search().filter('term', foo=666)[0]
    <SimpleObject_ElasticSearchResult: SimpleObject_ElasticSearchResult object>
    >>> SimpleObject.search_objects.search().filter('term', foo=666)[0].foo
    666

This manager returns "shallow" versions of your Django model. Specifically, it might leave off some fields (depending or your indexing), and the `save()` method will be unavilable. If you want to get full Django objects, you can chain the `.full()` method, like so:

    >>> SimpleObject.search_objects.search().filter('term', foo=1).full()[0]
    <SimpleObject: SimpleObject object>

Note that this will have a performance impact, as you are performing an Elasticsearch query, and then at least one database query.
