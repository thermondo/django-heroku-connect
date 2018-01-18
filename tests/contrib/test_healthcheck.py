import secrets
from unittest import mock

import pytest
from health_check.exceptions import ServiceUnavailable

from heroku_connect.contrib.heroku_connect_health_check.backends import (
    HerokuConnectHealthCheck
)
from tests.test_utils import (
    ALL_CONNECTIONS_API_CALL_OUTPUT, CONNECTION_DETAILS_API_CALL_OUTPUT,
    MockUrlLibResponse
)


@mock.patch('urllib.request.urlopen')
def test_check_status(mock_get):
    mock_get.side_effect = [MockUrlLibResponse(ALL_CONNECTIONS_API_CALL_OUTPUT),
                            MockUrlLibResponse(CONNECTION_DETAILS_API_CALL_OUTPUT)]
    assert HerokuConnectHealthCheck().check_status()


@mock.patch('urllib.request.urlopen')
def test_settings_exception(mock_get, settings):
    mock_get.side_effect = [MockUrlLibResponse(ALL_CONNECTIONS_API_CALL_OUTPUT),
                            MockUrlLibResponse(CONNECTION_DETAILS_API_CALL_OUTPUT)]
    settings.HEROKU_AUTH_TOKEN = None
    settings.HEROKU_CONNECT_APP_NAME = secrets.token_urlsafe()
    with pytest.raises(ServiceUnavailable):
        HerokuConnectHealthCheck().check_status()

    settings.HEROKU_AUTH_TOKEN = secrets.token_urlsafe()
    settings.HEROKU_CONNECT_APP_NAME = None
    with pytest.raises(ServiceUnavailable):
        HerokuConnectHealthCheck().check_status()

    settings.HEROKU_AUTH_TOKEN = None
    settings.HEROKU_CONNECT_APP_NAME = None
    with pytest.raises(ServiceUnavailable):
        HerokuConnectHealthCheck().check_status()


@mock.patch('urllib.request.urlopen')
def test_health_check_url(mock_get, client):
    mock_get.side_effect = [MockUrlLibResponse(ALL_CONNECTIONS_API_CALL_OUTPUT),
                            MockUrlLibResponse(CONNECTION_DETAILS_API_CALL_OUTPUT)]
    response = client.get('/ht/')
    assert response.status_code == 200
    assert b'<td>Heroku Connect</td>' in response.content
