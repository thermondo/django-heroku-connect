from django.db import connections
from django.db.backends.postgresql.creation import (
    DatabaseCreation as _DatabaseCreation
)
from django.db.models.signals import pre_migrate

from heroku_connect.conf import settings
from heroku_connect.utils import get_heroku_connect_models


SCHEMA_EXISTS_QUERY = """
SELECT exists(
  SELECT schema_name
   FROM information_schema.schemata
    WHERE schema_name = %s
    );
"""


class DatabaseCreation(_DatabaseCreation):

    def create_test_db(self, *args, **kwargs):
        def _migrate_hc_schema(using, **kwargs):
            connection = connections[using]
            with connection.cursor() as cursor:
                cursor.execute(SCHEMA_EXISTS_QUERY, [settings.HEROKU_CONNECT_SCHEMA])
                schema_exists = cursor.fetchone()[0]
                if not schema_exists:
                    cursor.execute("CREATE SCHEMA %s;" % settings.HEROKU_CONNECT_SCHEMA)

                    with connection.schema_editor() as editor:
                        for model in get_heroku_connect_models():
                            editor.create_model(model)

            assert pre_migrate.disconnect(_migrate_hc_schema), "Run only once."

        pre_migrate.connect(_migrate_hc_schema)
        return super().create_test_db(*args, **kwargs)
