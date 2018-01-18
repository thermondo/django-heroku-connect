from unittest import mock

from heroku_connect.contrib.health_check import HerokuConnectHealthCheck
from tests.test_utils import (
    ALL_CONNECTIONS_API_CALL_OUTPUT, CONNECTION_DETAILS_API_CALL_OUTPUT,
    MockUrlLibResponse
)


@mock.patch('urllib.request.urlopen')
def test_check_status(mock_get):
    mock_get.side_effect = [MockUrlLibResponse(ALL_CONNECTIONS_API_CALL_OUTPUT),
                            MockUrlLibResponse(CONNECTION_DETAILS_API_CALL_OUTPUT)]
    assert(HerokuConnectHealthCheck().check_status())
