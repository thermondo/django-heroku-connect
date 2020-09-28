import copy
import json

import httpretty
import pytest
from django.db import connection
from django.utils import timezone

from heroku_connect.db.models.base import READ_WRITE, HerokuConnectModel
from heroku_connect.models import (
    TRIGGER_LOG_ACTION, TRIGGER_LOG_STATE, TriggerLog, TriggerLogArchive
)
from heroku_connect.utils import (
    get_connected_model_for_table_name, get_unique_connection_write_mode
)
from tests import fixtures


def make_trigger_log_for_model(model, *, is_archived=False, **kwargs):
    kwargs.setdefault('table_name', model.get_heroku_connect_table_name())
    kwargs.setdefault('record_id', model.id)
    kwargs.setdefault('created_at', timezone.now())
    log = make_trigger_log(is_archived=is_archived, **kwargs)
    return log


def make_trigger_log(*, is_archived=False, **attrs):
    """
    Make an unsaved trigger log instance from given attributes.

    Args:
        is_archived (bool): Make a TriggerLog instance if ``True``, a TriggerLogArchive otherwise
        **attrs: Attributes of the trigger log instance

    Returns:
        An unsaved TriggerLog or TriggerLogArchive instance, depending on whether `is_archived`
        is False or True.
    """
    model_cls = TriggerLogArchive if is_archived else TriggerLog
    attrs.setdefault('state', TRIGGER_LOG_STATE['NEW'])
    attrs.setdefault('action', TRIGGER_LOG_ACTION['INSERT'])
    attrs.setdefault('table_name', 'SOME_TABLE')
    attrs.setdefault('record_id', 12345)
    return model_cls(**attrs)


@pytest.fixture
def hc_capture_stored_procedures(db, settings):
    # to capture:
    # > select routine_definition from information_schema.routines
    # > where routine_name = 'hc_capture_insert_from_row';
    # parameters following https://dataedo.com/kb/query/postgresql/list-stored-procedure-parameters

    with connection.cursor() as cursor:
        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {settings.HEROKU_CONNECT_SCHEMA}.hc_capture_insert_from_row
                (source_row hstore, table_name text, excluded_cols text[] default ARRAY[]::text[])
            RETURNS int
            LANGUAGE plpgsql
            AS $$

            DECLARE
                excluded_cols_standard text[] = ARRAY['_hc_lastop', '_hc_err']::text[];
                retval int;

            BEGIN
                -- VERSION 1 --

                IF (source_row -> 'id') IS NULL THEN
                    -- source_row is required to have an int id value
                    RETURN NULL;
                END IF;

                excluded_cols_standard := array_remove(
                    array_remove(excluded_cols, 'id'), 'sfid') || excluded_cols_standard;
                INSERT INTO "salesforce"."_trigger_log" (
                    action, table_name, txid, created_at, state, record_id, values)
                VALUES (
                    'INSERT', table_name, txid_current(), clock_timestamp(), 'NEW',
                    (source_row -> 'id')::int,
                    source_row - excluded_cols_standard
                ) RETURNING id INTO retval;
                RETURN retval;
            END;
            $$
        """)

        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {settings.HEROKU_CONNECT_SCHEMA}.hc_capture_update_from_row
            (source_row hstore, table_name text, columns_to_include text[] default ARRAY[]::text[])
            RETURNS int
            LANGUAGE plpgsql
            AS $$
            DECLARE
                excluded_cols_standard text[] = ARRAY['_hc_lastop', '_hc_err']::text[];
                excluded_cols text[];
                retval int;

            BEGIN
                -- VERSION 1 --

                IF (source_row -> 'id') IS NULL THEN
                    -- source_row is required to have an int id value
                    RETURN NULL;
                END IF;

                IF array_length(columns_to_include, 1) <> 0 THEN
                    excluded_cols := array(
                        select skeys(source_row)
                        except
                        select unnest(columns_to_include)
                    );
                END IF;
                excluded_cols_standard := excluded_cols || excluded_cols_standard;
                INSERT INTO "salesforce"."_trigger_log" (
                   action, table_name, txid, created_at, state, record_id, sfid, values, old)
                VALUES (
                   'UPDATE', table_name, txid_current(), clock_timestamp(), 'NEW',
                   (source_row -> 'id')::int, source_row -> 'sfid',
                   source_row - excluded_cols_standard, NULL
                ) RETURNING id INTO retval;
                RETURN retval;
                END;
            $$
        """)


@pytest.fixture()
def connected_class():
    """Get a HerokuConnectedModel subclass"""
    # The class definition is hidden in a fixture to keep the app registry and database table space
    # clean for other tests.
    global __ConnectedTestModel
    try:
        cls = __ConnectedTestModel
        meta = cls._meta
        meta.apps.register_model(meta.app_label, cls)
    except NameError:
        # define the class only once, or django will warn about redefining models
        class ConnectedTestModel(HerokuConnectModel):
            sf_object_name = 'CONNECTED_TEST_MODEL'
            sf_access = READ_WRITE

            class Meta:
                app_label = 'tests'

        cls = __ConnectedTestModel = ConnectedTestModel
        meta = cls._meta
        # creating the class automatically registers it

    # create the model table (let django's test cases roll this back automatically)
    with connection.schema_editor() as editor:
        editor.create_model(cls)

    try:
        yield cls  # run test
    finally:
        # de-register class from Apps registry
        testapp_models = meta.apps.all_models.get(meta.app_label, {})
        registered_name = None
        for name, model_cls in testapp_models.items():
            if model_cls is cls:
                registered_name = name
        if registered_name:
            del testapp_models[registered_name]


@pytest.fixture()
def connected_model(connected_class):
    return connected_class.objects.create()


@pytest.fixture()
def trigger_log(connected_model):
    return make_trigger_log_for_model(connected_model, is_archived=False)


@pytest.fixture()
def archived_trigger_log(connected_model):
    return make_trigger_log_for_model(connected_model, is_archived=True)


@pytest.fixture()
def failed_trigger_log(connected_model):
    return make_trigger_log_for_model(connected_model,
                                      is_archived=False,
                                      state=TRIGGER_LOG_STATE['FAILED'])


@pytest.yield_fixture
def set_write_mode_merge():
    get_unique_connection_write_mode.cache_clear()
    with httpretty.enabled():
        httpretty.register_uri(
            httpretty.GET,
            'https://connect-eu.heroku.com/api/v3/connections',
            body=json.dumps(fixtures.connections),
            status=200,
            content_type='application/json',
        )
        yield


@pytest.yield_fixture
def set_write_mode_ordered():
    get_unique_connection_write_mode.cache_clear()
    connections = copy.deepcopy(fixtures.connections)
    connections['results'][0]['features'] = dict(poll_db_no_merge=True)

    with httpretty.enabled():
        httpretty.register_uri(
            httpretty.GET,
            'https://connect-eu.heroku.com/api/v3/connections',
            body=json.dumps(connections),
            status=200,
            content_type='application/json',
        )
        yield
