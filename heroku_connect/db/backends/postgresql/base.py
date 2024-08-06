from django.db.backends.postgresql.base import (
    DatabaseWrapper as PostgresDatabaseWrapper,
)

from heroku_connect.db.backends.base.base import HerokuConnectDatabaseWrapperMixin


class DatabaseWrapper(HerokuConnectDatabaseWrapperMixin, PostgresDatabaseWrapper):
    display_name = "PostgreSQL with Heroku Connect"
