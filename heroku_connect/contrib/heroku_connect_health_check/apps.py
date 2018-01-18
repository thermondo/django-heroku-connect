from django.apps import AppConfig
from health_check.plugins import plugin_dir


class HealthCheckConfig(AppConfig):
    name = 'heroku_connect.contrib.heroku_connect_health_check'

    def ready(self):
        from .backends import HerokuConnectHealthCheck
        plugin_dir.register(HerokuConnectHealthCheck)
