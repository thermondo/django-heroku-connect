from ....conf import settings
from .creation import DatabaseCreation


class HerokuConnectDatabaseWrapperMixin:
    creation_class = DatabaseCreation
    search_path = 'public,%s,pg_catalog' % settings.HEROKU_CONNECT_SCHEMA

    def __init__(self, settings_dict, *args, **kwargs):
        settings_dict['OPTIONS'].setdefault('options', '-c search_path=%s' % self.search_path)
        super().__init__(settings_dict, *args, **kwargs)
