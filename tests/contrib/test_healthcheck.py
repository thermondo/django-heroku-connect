import json
import secrets

import httpretty
import pytest
from health_check.exceptions import (
    ServiceReturnedUnexpectedResult, ServiceUnavailable
)

from heroku_connect.contrib.heroku_connect_health_check.backends import (
    HerokuConnectHealthCheck
)
from tests import fixtures


@httpretty.activate
def test_check_status():
    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
        body=json.dumps(fixtures.connections),
        status=200,
        content_type='application/json',
    )
    hc = HerokuConnectHealthCheck()
    hc.check_status()
    assert not hc.errors

    connection = fixtures.connection.copy()
    connection['state'] = 'error'
    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
        body=json.dumps({'results': [connection]}),
        status=200,
        content_type='application/json',
    )
    hc = HerokuConnectHealthCheck()
    hc.check_status()
    assert hc.errors
    assert hc.errors[0].message == "Connection state for 'sample name' is 'error'"

    connection['state'] = 'error'
    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
        body=json.dumps({'errors': 'unknown error'}),
        status=500,
        content_type='application/json',
    )
    hc = HerokuConnectHealthCheck()
    with pytest.raises(ServiceReturnedUnexpectedResult) as e:
        hc.check_status()

    assert 'Unable to retrieve connection state' in str(e.value)


def test_settings_exception(settings):
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


@httpretty.activate
def test_health_check_url(client):
    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
        body=json.dumps(fixtures.connections),
        status=200,
        content_type='application/json',
    )
    response = client.get('/ht/')
    assert response.status_code == 200
    assert b'<td>Heroku Connect</td>' in response.content
