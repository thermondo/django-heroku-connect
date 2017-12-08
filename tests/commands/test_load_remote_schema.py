import os
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from heroku_connect.management.commands.load_remote_schema import Command
from heroku_connect.test.utils import heroku_cli


class TestLoadRemoteSchema:
    pg_url = 'postgres://brucewayne:batman@secret.server.gov:1234/gotham'

    def test_get_database_url(self):
        with heroku_cli('▸    No app specified', exit_code=1):
            with pytest.raises(CommandError) as e:
                Command.get_database_url(None)

        assert 'Please provide the correct Heroku app name.' in str(e)

        with heroku_cli(self.pg_url, exit_code=0):
            assert self.pg_url in Command.get_database_url(None)

        with heroku_cli(self.pg_url, exit_code=0):
            assert self.pg_url in Command.get_database_url('ninja')

    def test_parse_url(self):
        credentials = Command().parse_credentials(self.pg_url)

        assert credentials['user'] == 'brucewayne'
        assert credentials['passwd'] == 'batman'
        assert credentials['host'] == 'secret.server.gov'
        assert credentials['port'] == '1234'
        assert credentials['dbname'] == 'gotham'

        with pytest.raises(CommandError) as e:
            Command().parse_credentials('not.a.valid.url')
        assert 'Could not parse DATABASE_URL.' in str(e)

    def test_get_schema(self):
        os.system('echo \'DROP SCHEMA IF EXISTS "salesforce" CASCADE;\''
                  ' | psql -d heroku_connect_test -a')
        with pytest.raises(CommandError) as e:
            Command.get_schema('', 'localhost', '5432',
                               'heroku_connect_test', '', 'salesforce')
        assert 'Schema not found.' in str(e)
        os.system('echo \'CREATE SCHEMA IF NOT EXISTS "salesforce";\''
                  ' | psql -d heroku_connect_test -a')
        response = Command.get_schema('', 'localhost', '5432',
                                      'heroku_connect_test', '', 'salesforce')
        assert 'PostgreSQL database dump' in response

    def test_call_command(self):
        os.system('echo \'CREATE SCHEMA IF NOT EXISTS "salesforce";\''
                  ' | psql -d heroku_connect_test -a')
        with heroku_cli('postgres://:@localhost:5432/heroku_connect_test', exit_code=0):
            with StringIO() as sql:
                call_command('load_remote_schema', stdout=sql)
                sql.seek(0)
                assert 'CREATE SCHEMA salesforce;' in sql.read()
