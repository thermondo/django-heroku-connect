from django.db.backends.postgresql.base import *  # NoQA

from heroku_connect.db.backends.base.base import (
    HerokuConnectDatabaseWrapperMixin
)


class DatabaseWrapper(HerokuConnectDatabaseWrapperMixin, DatabaseWrapper):
    display_name = 'PostgreSQL with Heroku Connect'
