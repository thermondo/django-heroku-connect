from django.contrib.gis.db.backends.postgis.base import (
    DatabaseWrapper as PostGisDatabaseWrapper,
)

from heroku_connect.db.backends.base.base import HerokuConnectDatabaseWrapperMixin


class DatabaseWrapper(HerokuConnectDatabaseWrapperMixin, PostGisDatabaseWrapper):
    display_name = "PostgreSQL with PostGIS and Heroku Connect"
