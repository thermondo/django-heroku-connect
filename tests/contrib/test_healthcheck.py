from unittest import mock

from heroku_connect.contrib.health_check import HerokuConnectHealthCheck


ALL_CONNECTIONS_API_CALL_OUTPUT = """{
        "count": 1,
        "results": [
            {
              "id": "1",
              "name": "sample name",
              "resource_name": "resource name"
            }
        ]
    }"""

CONNECTION_DETAILS_API_CALL_OUTPUT = """{
        "id": "1",
        "name": "sample name",
        "resource_name": "resource name",
        "schema_name": "salesforce",
        "db_key": "DATABASE_URL",
        "state": "IDLE",
        "mappings": [
            {
              "id": "XYZ",
              "object_name": "Account",
              "state": "SCHEMA_CHANGED"
            }
        ]
    }"""


@mock.patch('subprocess.check_output')
def test_all_connections_api(mock_get):
    mock_get.return_value = ALL_CONNECTIONS_API_CALL_OUTPUT
    assert(HerokuConnectHealthCheck().get_connection_id() == '1')


@mock.patch('subprocess.check_output')
def test_connection_detail_api(mock_get):
    mock_get.return_value = CONNECTION_DETAILS_API_CALL_OUTPUT
    assert(HerokuConnectHealthCheck().get_connection_status(1))


@mock.patch('subprocess.check_output')
def test_check_status(mock_get):
    mock_get.side_effect = [ALL_CONNECTIONS_API_CALL_OUTPUT,
                            CONNECTION_DETAILS_API_CALL_OUTPUT]
    assert(HerokuConnectHealthCheck().check_status())
