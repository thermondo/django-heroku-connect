import pytest
from django.db import connection


@pytest.fixture
def hc_capture_stored_procedures(db, settings):
    # to capture:
    # > select routine_definition from information_schema.routines
    # > where routine_name = 'hc_capture_insert_from_row';
    # or in psql:
    # > \sf salesforce.hc_capture_insert_from_row
    # parameters following https://dataedo.com/kb/query/postgresql/list-stored-procedure-parameters

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
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
        """
        )

        cursor.execute(
            f"""
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
        """
        )
