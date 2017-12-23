from django.db.backends.postgresql.base import *  # NoQA

from ..base.base import HerokuConnectDatabaseWrapperMixin


class DatabaseWrapper(HerokuConnectDatabaseWrapperMixin, DatabaseWrapper):
    display_name = 'PostgreSQL with Heroku Connect'
