import datetime
import json

import httpretty
import pytest
import requests
from django.db import models

from heroku_connect import utils
from heroku_connect.db.models import HerokuConnectModel

from . import fixtures


def test_get_heroku_connect_models():
    try:
        class MyModel(HerokuConnectModel):
            sf_object_name = 'Test__c'

            class Meta:
                app_label = 'tests.testapp'
                abstract = True

        assert MyModel not in list(utils.get_heroku_connect_models())

        class MyModel(HerokuConnectModel):
            sf_object_name = 'Test__c'

            class Meta:
                app_label = 'tests.testapp'

        assert MyModel in list(utils.get_heroku_connect_models())

        class MyRegularModel(models.Model):
            class Meta:
                app_label = 'tests.testapp'

        assert MyRegularModel not in list(utils.get_heroku_connect_models())

        class AbstratHCModel(HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            class Meta:
                app_label = 'tests.testapp'
                abstract = False

        class RegularModel(AbstratHCModel):
            class Meta:
                app_label = 'tests.testapp'

        assert RegularModel not in list(utils.get_heroku_connect_models())

    finally:
        from django.apps import apps
        apps.all_models['tests.testapp'] = {}


def test_get_mapping(settings):
    settings.HEROKU_CONNECT_APP_NAME = 'ninja'
    settings.HEROKU_CONNECT_ORGANIZATION_ID = '1234567890'
    exported_at = datetime.datetime(2001, 5, 24)

    mapping = utils.get_mapping(exported_at=exported_at)
    assert mapping['connection'] == {
        'app_name': 'ninja',
        'exported_at': '2001-05-24T00:00:00',
        'organization_id': '1234567890',
    }

    assert {
               'config': {
                   'access': 'read_write',
                   'fields': {
                       'A_Number__c': {},
                       'External_ID': {},
                       'Id': {},
                       'IsDeleted': {},
                       'SystemModstamp': {},
                   },
                   'indexes': {
                       'Id': {'unique': True},
                       'SystemModstamp': {'unique': False},
                       'External_ID': {'unique': True},
                   },
                   'sf_max_daily_api_calls': 30000,
                   'sf_notify_enabled': False,
                   'sf_polling_seconds': 600,
                   'upsert_field': 'External_ID',
               },
               'object_name': 'Number_Object__c',
           } in mapping['mappings']
    assert {
               'config': {
                   'access': 'read_write',
                   'fields': {
                       'A_DateTime__c': {},
                       'Id': {},
                       'IsDeleted': {},
                       'SystemModstamp': {}
                   },
                   'indexes': {
                       'Id': {'unique': True},
                       'SystemModstamp': {'unique': False}
                   },
                   'sf_max_daily_api_calls': 30000,
                   'sf_notify_enabled': False,
                   'sf_polling_seconds': 600,
               },
               'object_name': 'DateTime_Object__c'
           } in mapping['mappings']

    assert mapping['version'] == 1


@httpretty.activate
def test_get_connections():
    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
        body=json.dumps(fixtures.connections),
        status=200,
        content_type='application/json',
    )
    assert utils.get_connections('ninja') == [fixtures.connection]

    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
        body=json.dumps({'error': 'something is wrong'}),
        status=500,
        content_type='application/json',
    )
    with pytest.raises(requests.HTTPError):
        utils.get_connections('ninja')

    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections",
        body='not-a-json',
        status=200,
        content_type='application/json',
    )
    with pytest.raises(ValueError):
        utils.get_connections('ninja')


@httpretty.activate
def test_get_connection():
    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections/1",
        body=json.dumps(fixtures.connection),
        status=200,
        content_type='application/json',
    )
    assert utils.get_connection('1') == fixtures.connection

    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections/1",
        body=json.dumps({'error': 'something is wrong'}),
        status=500,
        content_type='application/json',
    )
    with pytest.raises(requests.HTTPError):
        utils.get_connection('1')

    httpretty.register_uri(
        httpretty.GET, "https://connect-eu.heroku.com/api/v3/connections/1",
        body='not-a-json',
        status=200,
        content_type='application/json',
    )
    with pytest.raises(ValueError):
        utils.get_connection('1')


@httpretty.activate
def test_import_mapping():
    httpretty.register_uri(
        httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
        data={'message': 'success'},
        status=200,
        content_type='application/json',
    )
    utils.import_mapping('1', {})

    httpretty.register_uri(
        httpretty.POST, "https://connect-eu.heroku.com/api/v3/connections/1/actions/import",
        data={'error': 'something is wrong'},
        status=500,
        content_type='application/json',
    )
    with pytest.raises(requests.HTTPError):
        utils.import_mapping('1', {})


@httpretty.activate
def test_link_connection_to_account():
    httpretty.register_uri(
        httpretty.POST, "https://connect-eu.heroku.com/api/v3/users/me/apps/ninja/auth",
        body=json.dumps({'results': []}),
        status=200,
        content_type='application/json',
    )
    utils.link_connection_to_account('ninja')

    httpretty.register_uri(
        httpretty.POST, "https://connect-eu.heroku.com/api/v3/users/me/apps/ninja/auth",
        body=json.dumps({'error': 'permission denied'}),
        status=403,
        content_type='application/json',
    )
    with pytest.raises(requests.HTTPError):
        utils.link_connection_to_account('ninja')

    httpretty.register_uri(
        httpretty.POST, "https://connect-eu.heroku.com/api/v3/users/me/apps/ninja/auth",
        body=json.dumps({'error': 'not found'}),
        status=404,
        content_type='application/json',
    )
    with pytest.raises(requests.HTTPError):
        utils.link_connection_to_account('ninja')


def test_get_connected_model_for_table_name(db, connected_class):
    table_name = connected_class.get_heroku_connect_table_name()
    assert connected_class is utils.get_connected_model_for_table_name(table_name)

    with pytest.raises(LookupError):
        utils.get_connected_model_for_table_name("NOBODY'S_TABLE_NAME")


@pytest.mark.parametrize("input_,expected", [
    ("", {}),
    (
        '"id"=>"429161", "name"=>"Kalkenbergerstr,43 "',
        {"id": "429161", "name": "Kalkenbergerstr,43 "}
    ),
    (
        '"line_break"=>"429\n161"',
        {"line_break": "429\n161"},
    ),
    (
        '"comma"=>"comma,comma"',
        {"comma": "comma,comma"},
    )
])
def test_hstore_test_to_dict(input_, expected):
    assert utils.hstore_text_to_dict(input_) == expected
