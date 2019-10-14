import io
import json

import httpretty
import pytest
from django.core.management import CommandError, call_command

from heroku_connect.management.commands.import_mappings import Command
from tests import fixtures


class TestImportMapping:

    @httpretty.activate
    def test_app_name(self):
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'message': 'success'},
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps(fixtures.connections),
            status=200,
            content_type='application/json',
        )
        call_command('import_mappings', '--app', 'ninja')

    @httpretty.activate
    def test_connection_id(self):
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'message': 'success'},
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps(fixtures.connections),
            status=200,
            content_type='application/json',
        )
        call_command('import_mappings', '--connection', '1')

    @httpretty.activate
    def test_no_app_no_connection_id(self):
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'message': 'success'},
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps(fixtures.connections),
            status=200,
            content_type='application/json',
        )
        with pytest.raises(CommandError) as e:
            call_command('import_mappings')
        assert "You need ether specify the application name or the connection ID." in str(e.value)

    @httpretty.activate
    def test_no_connections(self):
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'message': 'success'},
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps({'results': []}),
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/users/me/apps/ninja/auth",
            body=json.dumps({'results': []}),
            status=200,
            content_type='application/json',
        )
        with io.StringIO() as stdout:
            with pytest.raises(CommandError) as e:
                call_command('import_mappings',
                             '--app', 'ninja',
                             '--wait-interval', '0',  # don't need to wait when mocking calls
                             stdout=stdout)
            stdout.seek(0)
            console = stdout.read()
        assert ("No associated connections found"
                " for the current user with the app 'ninja'.") in str(e.value)
        assert console == (
            "Fetching connections.\n"
            "No associated connections found for the current user with the app 'ninja'.\n"
            "Linking the current user with Heroku Connect.\n"
            "Fetching connections.\n"
        )

    @httpretty.activate
    def test_authentication_failed(self):
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'message': 'success'},
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps({'results': []}),
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/users/me/apps/ninja/auth",
            body=json.dumps({'error': 'permission denied'}),
            status=403,
            content_type='application/json',
        )
        with io.StringIO() as stdout:
            with pytest.raises(CommandError) as e:
                call_command('import_mappings', '--app', 'ninja', stdout=stdout)
            stdout.seek(0)
            console = stdout.read()
        assert "Authentication failed" in str(e.value)
        assert console == (
            "Fetching connections.\n"
            "No associated connections found for the current user with the app 'ninja'.\n"
            "Linking the current user with Heroku Connect.\n"
        )

    @httpretty.activate
    def test_multiple_connections(self):
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'message': 'success'},
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps({'results': [fixtures.connection, fixtures.connection]}),
            status=200,
            content_type='application/json',
        )
        with pytest.raises(CommandError) as e:
            call_command('import_mappings', '--app', 'ninja')
        assert ("More than one associated connections found"
                " for the current user with the app 'ninja'."
                " Please specify the connection ID.") in str(e.value)

    @httpretty.activate
    def test_upload_failed(self):
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'error': 'internal server error'},
            status=500,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps(fixtures.connections),
            status=200,
            content_type='application/json',
        )
        with pytest.raises(CommandError) as e:
            call_command('import_mappings', '--app', 'ninja')
        assert "Failed to upload the mapping" in str(e.value)

    @httpretty.activate
    def test_load_connection_failed(self):
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body="{'error': 'internal server error'}",
            status=500,
            content_type='application/json',
        )
        with pytest.raises(CommandError) as e:
            call_command('import_mappings', '--app', 'ninja')
        assert "Failed to load connections" in str(e.value)

    @httpretty.activate
    def test_waiting(self):
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections/1",
            body=json.dumps(fixtures.connection),
            status=200,
            content_type='application/json',
        )
        Command().wait_for_import('1', 0)

        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections/2",
            data={'error': 'internal server error'},
            status=500,
            content_type='application/json',
        )
        with pytest.raises(CommandError) as e:
            Command().wait_for_import('2', 0)
        assert 'Failed to fetch connection information.' in str(e.value)

        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections/1",
            body=json.dumps(fixtures.connection),
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
            data={'message': 'success'},
            status=200,
            content_type='application/json',
        )
        httpretty.register_uri(
            httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
            body=json.dumps(fixtures.connections),
            status=200,
            content_type='application/json',
        )
        call_command('import_mappings', '--app', 'ninja', '--wait', '--wait-interval', '0')
