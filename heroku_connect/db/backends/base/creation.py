from django.db.backends.postgresql.creation import (
    DatabaseCreation as _DatabaseCreation
)
from django.db.models.signals import pre_migrate

from heroku_connect.utils import create_heroku_connect_schema


def _create_heroku_connect_schema(sender, app_config, **kwargs):
    create_heroku_connect_schema(using=kwargs['using'])
    assert pre_migrate.disconnect(_create_heroku_connect_schema)


class DatabaseCreation(_DatabaseCreation):

    def create_test_db(self, *args, **kwargs):
        pre_migrate.connect(_create_heroku_connect_schema)
        return super().create_test_db(*args, **kwargs)
