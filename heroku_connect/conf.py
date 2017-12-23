import os

from appconf import AppConf
from django.conf import settings

__all__ = ('settings',)


class HerokuConnectAppConf(AppConf):
    HEROKU_CONNECT_SCHEMA = 'salesforce'
    """Database schema used by the Heroku Connect add-on."""

    HEROKU_CONNECT_ORGANIZATION_ID = os.environ.get('HEROKU_CONNECT_ORGANIZATION_ID', '')
    """
    `Salesforce Organization ID`_.

    This setting will have default based on the environment variable
    ``HEROKU_CONNECT_ORGANIZATION_ID``.

    Note:
        This is not preset on your Heroku application. You will need to either add a setting
        or set the environment variable manually.

    .. _`Salesforce Organization ID`: https://help.salesforce.com/articleView?id=000006019

    """

    HEROKU_CONNECT_APP_NAME = os.environ.get('HEROKU_APP_NAME', '')
    """
    Heroku application name.

    This setting will have default based on your environment
    should you have `Dyno Metadata`_ enabled.

    .. _`Dyno Metadata`:
        https://devcenter.heroku.com/articles/dyno-metadata

    """
