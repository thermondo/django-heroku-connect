from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import connection


class TestCreateDevelopmentSchema:

    def test_default(self, db):
        with connection.cursor() as c:
            c.execute('DROP SCHEMA salesforce CASCADE;')
        with StringIO() as sql:
            call_command('create_development_schema', stdout=sql)
            sql.seek(0)
            assert sql.read() == 'Schema salesforce created.\n'

    def test_exception(self, db):
        with pytest.raises(CommandError) as e:
            call_command('create_development_schema')

        assert 'Schema salesforce already exists.' in str(e.value)

    def test_force(self, db):
        with StringIO() as sql:
            call_command('create_development_schema', '--force', stdout=sql)
            sql.seek(0)
            assert sql.read() == 'Schema salesforce created.\n'
