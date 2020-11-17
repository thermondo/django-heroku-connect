import os
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command
from django.db import connection

from heroku_connect.management.commands.load_remote_schema import Command
from heroku_connect.test.utils import heroku_cli


class TestLoadRemoteSchema:
    pg_url = 'postgres://brucewayne:batman@secret.server.gov:1234/gotham'

    db = settings.DATABASES['default']

    def test_get_database_url(self):
        with heroku_cli('▸    No app specified', exit_code=1):
            with pytest.raises(CommandError) as e:
                Command.get_database_url(None)

        assert 'Please provide the correct Heroku app name.' in str(e.value)

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
        assert 'Could not parse DATABASE_URL.' in str(e.value)

    @pytest.mark.django_db
    def test_get_schema(self):
        with connection.cursor() as c:
            c.execute('DROP SCHEMA IF EXISTS "salesforce" CASCADE')

        get_schema_args = dict(
            user=self.db["USER"], 
            host=self.db["HOST"], 
            port=self.db["PORT"], 
            dbname=self.db["NAME"], 
            passwd=self.db["PASSWORD"], 
            schema_name="salesforce",
        )

        with pytest.raises(CommandError) as e:
            Command.get_schema(**get_schema_args)
        assert 'Schema not found.' in str(e.value)

        with connection.cursor() as c:
            c.execute('CREATE SCHEMA IF NOT EXISTS "salesforce"')

        response = Command.get_schema(**get_schema_args)
        assert 'PostgreSQL database dump' in response

    @pytest.mark.django_db
    def test_call_command(self):
        with connection.cursor() as c:
            c.execute('CREATE SCHEMA IF NOT EXISTS "salesforce"')

        database_url = (
            'postgres://'
            f'{self.db["USER"]}:{self.db["PASSWORD"]}'
            f'@{self.db["HOST"]}'
            f':{self.db["PORT"]}'
            f'/{self.db["NAME"]}'
        )
        with heroku_cli(database_url, exit_code=0):
            with StringIO() as sql:
                call_command('load_remote_schema', stdout=sql)
                sql.seek(0)
                assert 'CREATE SCHEMA salesforce;' in sql.read()
