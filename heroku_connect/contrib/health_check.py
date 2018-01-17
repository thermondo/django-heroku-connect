import logging

from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable

from ..conf import settings
from ..utils import get_connection_id, get_connection_status

logger = logging.getLogger('heroku-health-check')


class HerokuConnectHealthCheck(BaseHealthCheckBackend):
    """
    Health Check for Heroku Connect.

    Note:

        This features requires `django-health-check`_ to be installed.

    .. _`django-health-check`: https://github.com/KristianOellegaard/django-health-check
    """

    def check_status(self):
        if not (settings.HEROKU_AUTH_TOKEN and settings.HEROKU_CONNECT_APP_NAME):
            raise ServiceUnavailable('Both App Name and Auth Token are required')

        connection_id = get_connection_id()
        return get_connection_status(connection_id)
