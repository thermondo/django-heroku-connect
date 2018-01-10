from django.db import models
from django.utils import timezone

from heroku_connect import utils
from heroku_connect.db.models import HerokuConnectModel


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
    finally:
        from django.apps import apps
        apps.all_models['tests.testapp'] = {}


def test_get_mapping(settings):
    settings.HEROKU_CONNECT_APP_NAME = 'ninja'
    settings.HEROKU_CONNECT_ORGANIZATION_ID = '1234567890'
    exported_at = timezone.datetime(2001, 5, 24)
    from pprint import pprint
    pprint(utils.get_mapping(exported_at=exported_at))

    assert utils.get_mapping(exported_at=exported_at) == {
        'connection': {
            'app_name': 'ninja',
            'exported_at': '2001-05-24T00:00:00',
            'organization_id': '1234567890',
        },
        'mappings': [
            {
                'config': {
                    'access': 'read_only',
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
            },
            {
                'config': {
                    'access': 'read_only',
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
            },
        ],
        'version': 1,
    }

    assert utils.get_mapping()['mappings'] == [
        {
            'config': {
                'access': 'read_only',
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
        },
        {
            'config': {
                'access': 'read_only',
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
        },
    ]
