"""Health Check implementation for Heroku Connect."""

import logging

from ...conf import settings
from ...utils import get_connections

try:
    from health_check.backends import BaseHealthCheckBackend
    from health_check.exceptions import ServiceUnavailable
except ImportError:
    raise ImportError('django-health-check is needed for this featue, see \
        http://django-heroku-connect.readthedocs.io/en/latest/contrib.html')


logger = logging.getLogger('health-check')


class HerokuConnectHealthCheck(BaseHealthCheckBackend):
    def identifier(self):
        return "Heroku Connect"

    def check_status(self):
        if not (settings.HEROKU_AUTH_TOKEN and settings.HEROKU_CONNECT_APP_NAME):
            raise ServiceUnavailable('Both App Name and Auth Token are required')

        connections = get_connections(settings.HEROKU_CONNECT_APP_NAME)
        for connection in connections:
            if connection['state'] != 'IDLE':
                self.add_error(ServiceUnavailable(
                    "Connection state for '%s' is '%s'" % (
                        connection['name'], connection['state']
                    )
                ))
