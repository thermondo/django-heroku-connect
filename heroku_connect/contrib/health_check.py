import logging
import subprocess
import json

from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceReturnedUnexpectedResult

from ..conf import settings

logger = logging.getLogger('heroku-health-check')


class HerokuConnectHealthCheck(BaseHealthCheckBackend):
    """
    Health Check for Heroku Connect.

    This features requires `django-health-check`_ to be installed.

    .. _`django-health-check`: https://github.com/KristianOellegaard/django-health-check
    """
    def check_status(self):
        if not (settings.HEROKU_AUTH_TOKEN and settings.HEROKU_CONNECT_APP_NAME):
            raise ServiceUnavailable('Both App Name and Auth Token are required')

        connection_id = self.get_connection_id()
        return self.get_connection_status(connection_id)

    def get_connection_id(self):
        """
        Return ConnectionId from the JSON response of the connections api call.
        For more details check 'https://devcenter.heroku.com/articles/heroku-connect-api#step-4-retrieve-the-new-connection-s-id'

        Sample response from the api call is below::

          {
            "count": 1,
            "results":[{
                "id": "<connection_id>",
                "name": "<app_name>",
                "resource_name": "<resource_name>",
                …
            }],
            …
          }

        """
        run_args = ['curl',
                    '-H', '"Authorization: Bearer %s"' % settings.HEROKU_AUTH_TOKEN,
                    '%s/v3/connections?app=%s' % (settings.HEROKU_CONNECT_API_ENDPOINT,
                                                  settings.HEROKU_CONNECT_APP_NAME)
                    ]
        try:
            output = subprocess.check_output(run_args)
        except subprocess.SubprocessError as e:
            raise ServiceReturnedUnexpectedResult(e)

        json_output = json.loads(output)
        return json_output['results'][0]['id']

    def get_status_from_heroku_output(self, connection_id):
        """
        Get Connection Status from the JSON response of the connection detail call.
        For more details go to 'https://devcenter.heroku.com/articles/heroku-connect-api#step-8-monitor-the-connection-and-mapping-status'

        Sample output::

          {
            "id": "<connection_id>",
            "name": "<app_name>",
            "resource_name": "<resource_name>",
            "schema_name": "salesforce",
            "db_key": "DATABASE_URL",
            "state": "IDLE",
            "mappings":[
              {
                "id": "<mapping_id>",
                "object_name": "Account",
                "state": "SCHEMA_CHANGED",
                …
              },
              {
                "id": "<mapping_id>",
                "object_name": "Contact",
                "state": "SCHEMA_CHANGED",
                …
              },
              …
            ]
            …
          }
        """
        run_args = ['curl',
                    '-H', '"Authorization: Bearer %s"' % settings.HEROKU_AUTH_TOKEN,
                    '%s/connections/%s?deep=true' % (settings.HEROKU_CONNECT_API_ENDPOINT, connection_id)
                    ]
        try:
            output = subprocess.check_output(run_args)
        except subprocess.SubprocessError as e:
            raise ServiceReturnedUnexpectedResult(e)

        json_output = json.loads(output)
        connection_state = json_output['state']
        if connection_state == 'IDLE':
            return True
