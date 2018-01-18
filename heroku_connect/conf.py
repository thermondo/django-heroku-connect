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

    HEROKU_AUTH_TOKEN = os.environ.get('HEROKU_AUTH_TOKEN', '')
    """
    Heroku Platform API's Direct Authorization token.

    This setting is OPTIONAL. It is required only if you are using the
    :class:`health-check<.contrib.health_check.HerokuConnectHealthCheck>` application.

    To obtain this token, first we need to have a Heroku API token.

    API token can be fetched using command `heroku auth:token`.
    More about Heroku API tokens here -
    https://devcenter.heroku.com/articles/authentication#retrieving-the-api-token.

    After we have our API token, we can fetch the Direct Authentication token
    by using a process called Token Exchange.

    Complete details about this process are provided in this link -
    https://devcenter.heroku.com/articles/oauth#direct-authorization-token-exchange.
    """

    HEROKU_CONNECT_API_ENDPOINT = os.environ.get('HEROKU_CONNECT_API_ENDPOINT',
                                                 'https://connect-eu.heroku.com/api/v3')
    """
    Heroku Connect API Endpoint.

    This setting is OPTIONAL. It is required only if you are using the
    :class:`health-check<.contrib.health_check.HerokuConnectHealthCheck>` application.
    Default is ``https://connect-eu.heroku.com/api/v3``.

    Check your endpoints at this link -
    https://devcenter.heroku.com/articles/heroku-connect-api#endpoints.

    """
