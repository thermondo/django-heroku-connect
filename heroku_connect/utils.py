"""Utility methods for Django Heroku Connect."""
import os
from functools import lru_cache

import requests
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone
from psycopg2.extensions import AsIs

from .conf import settings
from .db.models.base import get_heroku_connect_table_name


class ConnectionStates:
    IDLE = 'IDLE'
    POLLING_DB_CHANGES = 'POLLING_DB_CHANGES'
    IMPORT_CONFIGURATION = 'IMPORT_CONFIGURATION'
    BUSY = 'BUSY'
    NEED_AUTHENTICATION = 'NEED_AUTHENTICATION'
    INACTIVE_ORG = 'INACTIVE_ORG'
    PAUSED = 'PAUSED'

    OK_STATES = (
        IDLE,
        POLLING_DB_CHANGES,
        IMPORT_CONFIGURATION,
        BUSY,
    )


def get_mapping(version=1, exported_at=None, app_name=None):
    """
    Return Heroku Connect mapping for the entire project.

    Args:
        version (int): Version of the Heroku Connect mapping, default: ``1``.
        exported_at (datetime.datetime): Time the export was created, default is ``now()``.
        app_name (str): Name of Heroku application associated with Heroku Connect the add-on.

    Returns:
        dict: Heroku Connect mapping.

    Note:
        The version does not need to be incremented. Exports from the Heroku Connect
        website will always have the version number ``1``.

    """
    if exported_at is None:
        exported_at = timezone.now()
    app_name = app_name or settings.HEROKU_CONNECT_APP_NAME
    return {
        'version': version,
        'connection': {
            'organization_id': settings.HEROKU_CONNECT_ORGANIZATION_ID,
            'app_name': app_name,
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


@lru_cache(maxsize=128)
def get_connected_model_for_table_name(table_name):
    """Return a connected model's table name (which read and written to by Heroku Connect)."""
    for connected_model in get_heroku_connect_models():
        if connected_model.get_heroku_connect_table_name() == table_name:
            return connected_model
    raise LookupError('No connected model found for table %r' % (table_name,))


_SCHEMA_EXISTS_QUERY = """
SELECT exists(
  SELECT schema_name
   FROM information_schema.schemata
    WHERE schema_name = %s
    );
"""

_TABLE_EXISTS_QUERY = """
SELECT EXISTS (
    SELECT 1
    FROM pg_tables
    WHERE schemaname = %(schema)s AND tablename = %(table)s
);
"""


def create_heroku_connect_schema(using=DEFAULT_DB_ALIAS):
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

        cursor.execute("CREATE SCHEMA %s;", [AsIs(settings.HEROKU_CONNECT_SCHEMA)])

    with connection.schema_editor() as editor:
        for model in get_heroku_connect_models():
            editor.create_model(model)
    return True


def create_trigger_log_tables(using=DEFAULT_DB_ALIAS):
    """
    Create the tables for the trigger log models in :mod:`heroku_connect.models`.

    Creating these tables manually should only be necessary for a local database.
    In a production environment, they are created and managed by Heroku Connect.

    Args:
        using (str): Alias for database connection.

    Returns:
        bool: ``True`` if the tables were created, ``False`` if they already exist.

    Raises:
        DatabaseError: if any of the tables already exists.

    """
    from heroku_connect.models import (TriggerLog, TriggerLogArchive)
    connection = connections[using]

    with connection.cursor() as cursor:
        params = {
            'schema': settings.HEROKU_CONNECT_SCHEMA,
            'table': get_heroku_connect_table_name(TriggerLog),
        }
        cursor.execute(_TABLE_EXISTS_QUERY, params)
        table_exists = cursor.fetchone()[0]
        if table_exists:
            return False

    with connection.schema_editor() as editor:
        for cls in [TriggerLog, TriggerLogArchive]:
            editor.create_model(cls)
    return True


def _get_authorization_headers():
    return {
        'Authorization': 'Bearer %s' % settings.HEROKU_AUTH_TOKEN
    }


def get_connections(app):
    """
    Return all Heroku Connect connections setup with the given application.

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


def import_mapping(connection_id, mapping):
    """
    Import Heroku Connection mapping for given connection.

    Args:
        connection_id (str): Heroku Connection connection ID.
        mapping (dict): Heroku Connect mapping.

    Raises:
        requests.HTTPError: If an error occurs uploading the mapping.
        ValueError: If the mapping is not JSON serializable.

    """
    url = os.path.join(settings.HEROKU_CONNECT_API_ENDPOINT,
                       'connections', connection_id, 'actions', 'import')

    response = requests.post(
        url=url,
        json=mapping,
        headers=_get_authorization_headers()
    )
    response.raise_for_status()


def link_connection_to_account(app):
    """
    Link the connection to your Heroku user account.

    https://devcenter.heroku.com/articles/heroku-connect-api#step-3-link-the-connection-to-your-heroku-user-account
    """
    url = os.path.join(settings.HEROKU_CONNECT_API_ENDPOINT, 'users', 'me', 'apps', app, 'auth')
    response = requests.post(
        url=url,
        headers=_get_authorization_headers()
    )
    response.raise_for_status()
