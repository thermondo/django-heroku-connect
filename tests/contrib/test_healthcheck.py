from unittest import mock

from heroku_connect import utils
from heroku_connect.contrib.health_check import HerokuConnectHealthCheck


class MockUrlLibResponse:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data.encode()


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


@mock.patch('urllib.request.urlopen')
def test_all_connections_api(mock_get):
    mock_get.return_value = MockUrlLibResponse(ALL_CONNECTIONS_API_CALL_OUTPUT)
    assert(utils.get_connection_id() == '1')


@mock.patch('urllib.request.urlopen')
def test_connection_detail_api(mock_get):
    mock_get.return_value = MockUrlLibResponse(CONNECTION_DETAILS_API_CALL_OUTPUT)
    assert(utils.get_connection_status(1))


@mock.patch('urllib.request.urlopen')
def test_check_status(mock_get):
    mock_get.side_effect = [MockUrlLibResponse(ALL_CONNECTIONS_API_CALL_OUTPUT),
                            MockUrlLibResponse(CONNECTION_DETAILS_API_CALL_OUTPUT)]
    assert(HerokuConnectHealthCheck().check_status())
