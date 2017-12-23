from django.db.backends.postgresql.base import *  # NoQA

from ....conf import settings
from .creation import DatabaseCreation


class DatabaseWrapper(DatabaseWrapper):
    creation_class = DatabaseCreation
    display_name = 'PostgreSQL with Heroku Connect'
    search_path = '"$user",public,%s' % settings.HEROKU_CONNECT_SCHEMA

    def __init__(self, settings_dict, *args, **kwargs):
        settings_dict['OPTIONS'].setdefault('options', '-c search_path=%s' % self.search_path)
        super().__init__(settings_dict, *args, **kwargs)
