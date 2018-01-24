"""Health Check implementation for Heroku Connect."""

import logging

import requests

from ... import utils
from ...conf import settings

try:
    from health_check.backends import BaseHealthCheckBackend
    from health_check.exceptions import (
        ServiceReturnedUnexpectedResult, ServiceUnavailable
    )
except ImportError as e:
    raise ImportError('django-health-check is needed for this featue, see \
        http://django-heroku-connect.readthedocs.io/en/latest/contrib.html') from e


logger = logging.getLogger('health-check')


class HerokuConnectHealthCheck(BaseHealthCheckBackend):
    def identifier(self):
        return "Heroku Connect"

    def check_status(self):
        if not (settings.HEROKU_AUTH_TOKEN and settings.HEROKU_CONNECT_APP_NAME):
            raise ServiceUnavailable('Both App Name and Auth Token are required')

        try:
            connections = utils.get_connections(settings.HEROKU_CONNECT_APP_NAME)
        except requests.HTTPError as e:
            raise ServiceReturnedUnexpectedResult("Unable to retrieve connection state") from e
        for connection in connections:
            if connection['state'] not in utils.ConnectionStates.OK_STATES:
                self.add_error(ServiceUnavailable(
                    "Connection state for '%s' is '%s'" % (
                        connection['name'], connection['state']
                    )
                ))
