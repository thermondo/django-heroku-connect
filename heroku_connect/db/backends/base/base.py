from heroku_connect.conf import settings
from heroku_connect.db.backends.base.creation import DatabaseCreation


class HerokuConnectDatabaseWrapperMixin:
    creation_class = DatabaseCreation
    search_path = f"public,{settings.HEROKU_CONNECT_SCHEMA},pg_catalog"

    def __init__(self, settings_dict, *args, **kwargs):
        settings_dict["OPTIONS"].setdefault(
            "options", f"-c search_path={self.search_path}"
        )
        super().__init__(settings_dict, *args, **kwargs)
