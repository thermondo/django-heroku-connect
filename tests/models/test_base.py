from django.core import checks
from django.db import models

from heroku_connect import models as hc_models


class TestHerokuConnectModelMixin:

    def test_meta(self, settings):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            class Meta:
                abstract = True

        assert MyModel._meta.db_table == '"salesforce"."my_object__c"'
        assert MyModel._meta.managed is False

        settings.HEROKU_CONNECT_SCHEMA = 'other_schema'

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            class Meta:
                abstract = True

        assert MyModel._meta.db_table == '"other_schema"."my_object__c"'

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            class Meta:
                abstract = True
                db_table = 'other_table_name'

        assert MyModel._meta.db_table == 'other_table_name'

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            class Meta:
                abstract = True
                managed = True

        assert MyModel._meta.managed is False

    def test_empty_mapping(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            class Meta:
                app_label = 'test'
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            'config':
                {
                    'access': 'read_only',
                    'fields': {
                        'ID': {},
                        'IsDeleted': {},
                        'SystemModstamp': {},
                    },
                    'indexes': {
                        'ID': {'unique': True},
                        'SystemModstamp': {'unique': False},
                    },
                    'sf_max_daily_api_calls': 30000,
                    'sf_notify_enabled': True,
                    'sf_polling_seconds': 120,
                },
            'object_name': 'My_Object__c'
        }

    def test_indexes(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            date1 = hc_models.DateTime(sf_field_name='Date1__c', db_index=True)
            date2 = hc_models.DateTime(sf_field_name='Date2__c', unique=True)
            date3 = hc_models.DateTime(sf_field_name='Date3__c', unique=True, db_index=True)

            class Meta:
                app_label = 'test'
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            'config':
                {
                    'access': 'read_only',
                    'fields': {
                        'ID': {},
                        'IsDeleted': {},
                        'SystemModstamp': {},
                        'Date1__c': {},
                        'Date2__c': {},
                        'Date3__c': {},
                    },
                    'indexes': {
                        'ID': {'unique': True},
                        'SystemModstamp': {'unique': False},
                        'Date1__c': {'unique': False},
                        'Date2__c': {'unique': True},
                        'Date3__c': {'unique': True},
                    },
                    'sf_max_daily_api_calls': 30000,
                    'sf_notify_enabled': True,
                    'sf_polling_seconds': 120,
                },
            'object_name': 'My_Object__c'
        }

    def test_upsert(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'

            date = hc_models.DateTime(sf_field_name='Date__c', upsert=True)

            class Meta:
                app_label = 'test'
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            'config':
                {
                    'access': 'read_only',
                    'fields': {
                        'ID': {},
                        'IsDeleted': {},
                        'SystemModstamp': {},
                        'Date__c': {},
                    },
                    'indexes': {
                        'ID': {'unique': True},
                        'SystemModstamp': {'unique': False},
                        'Date__c': {'unique': True},
                    },
                    'sf_max_daily_api_calls': 30000,
                    'sf_notify_enabled': True,
                    'sf_polling_seconds': 120,
                    'upsert_field': 'Date__c',
                },
            'object_name': 'My_Object__c',
        }

    def test_access(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'
            sf_access = 'read_write'

            class Meta:
                app_label = 'test'
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            'config':
                {
                    'access': 'read_write',
                    'fields': {
                        'ID': {},
                        'IsDeleted': {},
                        'SystemModstamp': {},
                    },
                    'indexes': {
                        'ID': {'unique': True},
                        'SystemModstamp': {'unique': False},
                    },
                    'sf_max_daily_api_calls': 30000,
                    'sf_notify_enabled': True,
                    'sf_polling_seconds': 120,
                },
            'object_name': 'My_Object__c'
        }

    def test_user(self):
        """
        Test ``User`` object edge case.

        See: https://help.heroku.com/sharing/5295ce37-d767-4355-aef7-95f3cde95915
        """
        class User(hc_models.HerokuConnectModel):
            sf_object_name = 'User'

            class Meta:
                abstract = True

        assert not any(f.name == 'is_deleted' for f in User._meta.fields)
        assert User.get_heroku_connect_field_mapping() == (
            {'ID': {}, 'SystemModstamp': {}},
            {'ID': {'unique': True}, 'SystemModstamp': {'unique': False}},
            None
        )

    def test_check_sf_object_name(self):
        class MyModel(hc_models.HerokuConnectModel):
            class Meta:
                app_label = 'test'
                abstract = True

        errors = MyModel.check()
        assert errors == [checks.Error(
            "test.MyModel must define a \"sf_object_name\".",
            id='heroku_connect.E001',
        )]

    def test_check_sf_access(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'Custom_Object__c'
            sf_access = 'wrong_value'

            class Meta:
                app_label = 'test'
                abstract = True

        errors = MyModel.check()
        assert errors == [checks.Error(
            "test.MyModel.sf_access must be one of ['read_only', 'read_write']",
            hint='wrong_value',
            id='heroku_connect.E002',
        )]

    def test_check_unique_sf_field_names(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'
            date1 = hc_models.DateTime(sf_field_name='Date1__c', db_column='date1')
            date2 = hc_models.DateTime(sf_field_name='Date1__c', db_column='date2')

            class Meta:
                app_label = 'test'
                abstract = True

        errors = MyModel.check()
        assert errors == [checks.Error(
            "test.MyModel has duplicate Salesforce field names.",
            hint=['Date1__c'],
            id='heroku_connect.E003',
        )]

    def test_check_upsert_field(self):
        class ExternalID(hc_models.HerokuConnectFieldMixin, models.CharField):
            def __init__(self, *args, **kwargs):
                kwargs['max_length'] = 18
                super().__init__(*args, **kwargs)

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = 'My_Object__c'
            extID1 = ExternalID(sf_field_name='extID1', upsert=True)
            extID2 = ExternalID(sf_field_name='extID2', upsert=True)

            class Meta:
                app_label = 'test'
                abstract = True

        errors = MyModel.check()
        assert errors == [checks.Error(
            "test.MyModel can only have a single upsert field.",
            hint=[
                MyModel._meta.get_field('extID1'),
                MyModel._meta.get_field('extID2'),
            ],
            id='heroku_connect.E004',
        )]
