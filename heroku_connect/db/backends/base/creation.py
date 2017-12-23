from django.db.backends.postgresql.creation import (
    DatabaseCreation as _DatabaseCreation
)
from django.db.models.signals import pre_migrate

from heroku_connect.utils import create_heroku_connect_schema


class DatabaseCreation(_DatabaseCreation):

    def create_test_db(self, *args, **kwargs):
        pre_migrate.connect(create_heroku_connect_schema)
        test_database_name = super().create_test_db(*args, **kwargs)
        assert pre_migrate.disconnect(create_heroku_connect_schema)
        return test_database_name
