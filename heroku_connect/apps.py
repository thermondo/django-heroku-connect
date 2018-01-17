from django.apps import AppConfig
from django.core import checks


class HerokuConnectAppConfig(AppConfig):
    """Heroku Connect Django App configuration."""

    name = 'heroku_connect'
    verbose_name = "Heroku Connect"

    def ready(self):
        from .checks import _check_foreign_key, _check_unique_sf_object_name

        checks.register(_check_foreign_key, checks.Tags.models)
        checks.register(_check_unique_sf_object_name, checks.Tags.models)
