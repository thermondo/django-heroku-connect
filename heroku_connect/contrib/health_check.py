from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceReturnedUnexpectedResult
import logging
import subprocess

from health_check.backends import BaseHealthCheckBackend
from ..conf import settings

logger = logging.getLogger('heroku-health-check')


class HerokuConnectHealthCheck(BaseHealthCheckBackend):
    def check_status(self):
        run_args = ['heroku', 'connect:info']
        heroku_app = settings.HEROKU_CONNECT_APP_NAME
        if heroku_app:
            run_args.extend(['-a', heroku_app])
        try:
            output = subprocess.check_output(run_args)
        except subprocess.SubprocessError as e:
            raise ServiceReturnedUnexpectedResult()
        else:
            return self.get_status_from_heroku_output(output.decode('utf-8'))

    def get_status_from_heroku_output(self, output):
        """Parse status to fetch Connection and Sync Status

        Sample output:
           Connection [7976d2d4-2483-4a75-9a97-7d7f0e879b21 / herokuconnect-asymmetrical-36239] (IDLE)
           --> Contact (DATA_SYNCED)
        """