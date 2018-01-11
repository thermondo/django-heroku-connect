from heroku_connect.contrib.health_check import HerokuConnectHealthCheck

from unittest import mock


@mock.patch('subprocess.check_output')
def test_all_connections_api(mock_get):
    all_connections_api_call_output = """{
        "count": 1,
        "results": [
            {
              "id": "1",
              "name": "sample name",
              "resource_name": "resource name"
            }
        ]
    }"""

    mock_get.return_value = all_connections_api_call_output
    assert(HerokuConnectHealthCheck().get_connection_id() == '1')


@mock.patch('subprocess.check_output')
def test_connection_detail_api(mock_get):
    connection_details_api_call_output = """{
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

    mock_get.return_value = connection_details_api_call_output
    assert(HerokuConnectHealthCheck().get_status_from_heroku_output(1))
