from django.contrib.gis.db.backends.postgis.base import *  # NoQA

from ..base.base import HerokuConnectDatabaseWrapperMixin


class DatabaseWrapper(HerokuConnectDatabaseWrapperMixin, DatabaseWrapper):
    display_name = 'PostgreSQL with PostGIS and Heroku Connect'
