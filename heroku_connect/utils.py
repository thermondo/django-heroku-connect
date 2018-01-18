"""Utility methods for Django Heroku Connect."""

import json
import urllib.request
from urllib.error import URLError

from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone

from .conf import settings


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


def get_connection_id():
    """
    Get the first Heroku Connect's Connection ID from the connections API response.

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

    Returns:
        String: The connection ID.

    Raises:
        URLError: An error occurred when accessing the connections API.

    """
    req = urllib.request.Request('%s/v3/connections?app=%s' % (
        settings.HEROKU_CONNECT_API_ENDPOINT, settings.HEROKU_CONNECT_APP_NAME))
    req.add_header('-H', '"Authorization: Bearer %s"' % settings.HEROKU_AUTH_TOKEN)
    try:
        output = urllib.request.urlopen(req)
    except URLError as e:
        raise URLError('Unable to fetch connections') from e

    json_output = json.load(output)
    return json_output['results'][0]['id']


def get_connection_status(connection_id):
    """
    Get Connection Status from the connection detail API response.

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

    Returns:
        String: State for the Heroku Connect's connection.

    Raises:
        URLError: An error occurred when accessing the connection detail API.

    """
    req = urllib.request.Request('%s/connections/%s?deep=true' % (
        settings.HEROKU_CONNECT_API_ENDPOINT, connection_id))
    req.add_header('-H', '"Authorization: Bearer %s"' % settings.HEROKU_AUTH_TOKEN)

    try:
        output = urllib.request.urlopen(req)
    except URLError as e:
        raise URLError('Unable to fetch connection details') from e

    json_output = json.load(output)
    return json_output['state']
