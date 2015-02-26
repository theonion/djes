from django.conf import settings as _settings

ES_CONNECTIONS = {
    "default": {
        "hosts": "localhost"
    }
}
ES_INDEX = _settings.DATABASES["default"]["NAME"]
