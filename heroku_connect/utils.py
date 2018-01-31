"""Utility methods for Django Heroku Connect."""
import os

import requests
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone

from .conf import settings


class ConnectionStates:
    IDLE = 'IDLE'
    POLLING_DB_CHANGES = 'POLLING_DB_CHANGES'
    IMPORT_CONFIGURATION = 'IMPORT_CONFIGURATION'
    NEED_AUTHENTICATION = 'NEED_AUTHENTICATION'

    OK_STATES = (
        IDLE,
        POLLING_DB_CHANGES,
        IMPORT_CONFIGURATION,
    )


def get_mapping(version=1, exported_at=None):
    """
    Return Heroku Connect mapping for the entire project.

    Args:
        version (int): Version of the Heroku Connect mapping, default: ``1``.
        exported_at (datetime.datetime): Time the export was created, default is ``now()``.

    Returns:
        dict: Heroku Connect mapping.

    Note:
        The version does not need to be incremented. Exports from the Heroku Connect
        website will always have the version number ``1``.

    """
    if exported_at is None:
        exported_at = timezone.now()
    return {
        'version': version,
        'connection': {
            'organization_id': settings.HEROKU_CONNECT_ORGANIZATION_ID,
            'app_name': settings.HEROKU_CONNECT_APP_NAME,
            'exported_at': exported_at.isoformat(),
        },
        'mappings': [
            model.get_heroku_connect_mapping()
            for model in get_heroku_connect_models()
        ]
    }


def get_heroku_connect_models():
    """
    Return all registered Heroku Connect Models.

    Returns:
        (Iterator):
            All registered models that are subclasses of `.HerokuConnectModel`.
            Abstract models are excluded, since they are not registered.

    """
    from django.apps import apps
    apps.check_models_ready()
    from heroku_connect.db.models import HerokuConnectModel

    return (
        model
        for models in apps.all_models.values()
        for model in models.values()
        if issubclass(model, HerokuConnectModel)
    )


_SCHEMA_EXISTS_QUERY = """
SELECT exists(
  SELECT schema_name
   FROM information_schema.schemata
    WHERE schema_name = %s
    );
"""


def create_heroku_connect_schema(using=DEFAULT_DB_ALIAS, **kwargs):
    """
    Create Heroku Connect schema.

    Note:
        This function is only meant to be used for local development.
        In a production environment the schema will be created by
        Heroku Connect.

    Args:
        using (str): Alias for database connection.

    Returns:
        bool: ``True`` if the schema was created, ``False`` if the
            schema already exists.

    """
    connection = connections[using]

    with connection.cursor() as cursor:
        cursor.execute(_SCHEMA_EXISTS_QUERY, [settings.HEROKU_CONNECT_SCHEMA])
        schema_exists = cursor.fetchone()[0]
        if schema_exists:
            return False

        cursor.execute("CREATE SCHEMA %s;" % settings.HEROKU_CONNECT_SCHEMA)

    with connection.schema_editor() as editor:
        for model in get_heroku_connect_models():
            editor.create_model(model)
    return True


def _get_authorization_headers():
    return {
        'Authorization': 'Bearer %s' % settings.HEROKU_AUTH_TOKEN
    }


def get_connections(app):
    """
    Return all Heroku Connect connections setup with the given app.

    For more details check the link -
    https://devcenter.heroku.com/articles/heroku-connect-api#step-4-retrieve-the-new-connection-s-id

    Sample response from the API call is below::

        {
            "count": 1,
            "results":[{
                "id": "<connection_id>",
                "name": "<app_name>",
                "resource_name": "<resource_name>",
                …
            }],
            …
        }

    Args:
        app (str): Heroku application name.

    Returns:
        List[dict]: List of all Heroku Connect connections associated with the Heroku application.

    Raises:
        requests.HTTPError: If an error occurred when accessing the connections API.
        ValueError: If response is not a valid JSON.

    """
    payload = {'app': app}
    url = os.path.join(settings.HEROKU_CONNECT_API_ENDPOINT, 'connections')
    response = requests.get(url, params=payload, headers=_get_authorization_headers())
    response.raise_for_status()
    return response.json()['results']


def get_connection(connection_id, deep=False):
    """
    Get Heroku Connection connection information.

    For more details check the link -
    https://devcenter.heroku.com/articles/heroku-connect-api#step-8-monitor-the-connection-and-mapping-status

    Sample response from API call is below::

        {
            "id": "<connection_id>",
            "name": "<app_name>",
            "resource_name": "<resource_name>",
            "schema_name": "salesforce",
            "db_key": "DATABASE_URL",
            "state": "IDLE",
            "mappings":[
                {
                    "id": "<mapping_id>",
                    "object_name": "Account",
                    "state": "SCHEMA_CHANGED",
                    …
                },
                {
                    "id": "<mapping_id>",
                    "object_name": "Contact",
                    "state": "SCHEMA_CHANGED",
                    …
                },
                …
            ]
            …
        }

    Args:
        connection_id (str): ID for Heroku Connect's connection.
        deep (bool): Return information about the connection’s mappings,
            in addition to the connection itself. Defaults to ``False``.

    Returns:
        dict: Heroku Connection connection information.

    Raises:
        requests.HTTPError: If an error occurred when accessing the connection detail API.
        ValueError: If response is not a valid JSON.

    """
    url = os.path.join(settings.HEROKU_CONNECT_API_ENDPOINT, 'connections', connection_id)
    payload = {'deep': deep}
    response = requests.get(url, params=payload, headers=_get_authorization_headers())
    response.raise_for_status()
    return response.json()
