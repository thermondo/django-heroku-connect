import os
import shutil

import pytest
from django.core import checks
from django.core.management import call_command
from django.db import models
from django.utils import timezone

from heroku_connect.db import models as hc_models
from heroku_connect.db.exceptions import WriteNotSupportedError
from tests.testapp.models import NumberModel


class TestHerokuConnectModelMixin:
    def test_meta(self, settings):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"

            class Meta:
                abstract = True

        assert MyModel._meta.db_table == 'salesforce"."my_object__c'
        assert MyModel._meta.managed is False
        assert MyModel.Meta.managed is False

        settings.HEROKU_CONNECT_SCHEMA = "other_schema"

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"

            class Meta:
                abstract = True

        assert MyModel._meta.db_table == 'other_schema"."my_object__c'

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"

            class Meta:
                abstract = True
                db_table = "other_table_name"

        assert MyModel._meta.db_table == "other_table_name"

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"

            class Meta:
                abstract = True
                managed = True

        assert MyModel._meta.managed is False
        assert MyModel.Meta.managed is False

    def test_migrations(self, db, settings):
        settings.MIGRATION_MODULES = {"testapp": "tests.testapp.migrations"}
        call_command("makemigrations", "testapp")
        with open(
            os.path.join(settings.BASE_DIR, "testapp/migrations/0001_initial.py")
        ) as f:
            migration = f.read()
        shutil.rmtree(os.path.join(settings.BASE_DIR, "testapp/migrations"))
        assert "'managed': False," in migration
        assert "'db_table': 'salesforce\".\"number_object__c'," in migration

    def test_empty_mapping(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"

            class Meta:
                app_label = "test"
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            "config": {
                "access": "read_only",
                "fields": {
                    "Id": {},
                    "IsDeleted": {},
                    "SystemModstamp": {},
                },
                "indexes": {
                    "Id": {"unique": True},
                    "SystemModstamp": {"unique": False},
                },
                "sf_max_daily_api_calls": 30000,
                "sf_notify_enabled": False,
                "sf_polling_seconds": 600,
            },
            "object_name": "My_Object__c",
        }

    def test_indexes(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"

            date1 = hc_models.DateTime(sf_field_name="Date1__c", db_index=True)
            date2 = hc_models.DateTime(sf_field_name="Date2__c", unique=True)
            date3 = hc_models.DateTime(
                sf_field_name="Date3__c", unique=True, db_index=True
            )

            class Meta:
                app_label = "test"
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            "config": {
                "access": "read_only",
                "fields": {
                    "Id": {},
                    "IsDeleted": {},
                    "SystemModstamp": {},
                    "Date1__c": {},
                    "Date2__c": {},
                    "Date3__c": {},
                },
                "indexes": {
                    "Id": {"unique": True},
                    "SystemModstamp": {"unique": False},
                    "Date1__c": {"unique": False},
                    "Date2__c": {"unique": True},
                    "Date3__c": {"unique": True},
                },
                "sf_max_daily_api_calls": 30000,
                "sf_notify_enabled": False,
                "sf_polling_seconds": 600,
            },
            "object_name": "My_Object__c",
        }

    def test_upsert(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"

            date = hc_models.DateTime(sf_field_name="Date__c", upsert=True)

            class Meta:
                app_label = "test"
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            "config": {
                "access": "read_only",
                "fields": {
                    "Id": {},
                    "IsDeleted": {},
                    "SystemModstamp": {},
                    "Date__c": {},
                },
                "indexes": {
                    "Id": {"unique": True},
                    "SystemModstamp": {"unique": False},
                    "Date__c": {"unique": True},
                },
                "sf_max_daily_api_calls": 30000,
                "sf_notify_enabled": False,
                "sf_polling_seconds": 600,
                "upsert_field": "Date__c",
            },
            "object_name": "My_Object__c",
        }

    def test_access(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            sf_access = "read_write"

            class Meta:
                app_label = "test"
                abstract = True

        mapping = MyModel.get_heroku_connect_mapping()
        assert mapping == {
            "config": {
                "access": "read_write",
                "fields": {
                    "Id": {},
                    "IsDeleted": {},
                    "SystemModstamp": {},
                },
                "indexes": {
                    "Id": {"unique": True},
                    "SystemModstamp": {"unique": False},
                },
                "sf_max_daily_api_calls": 30000,
                "sf_notify_enabled": False,
                "sf_polling_seconds": 600,
            },
            "object_name": "My_Object__c",
        }

    def test_user(self):
        """
        Test ``User`` object edge case.

        See: https://help.heroku.com/sharing/5295ce37-d767-4355-aef7-95f3cde95915
        """

        class User(hc_models.HerokuConnectModel):
            sf_object_name = "User"

            class Meta:
                abstract = True

        assert not any(f.name == "is_deleted" for f in User._meta.fields)
        assert User.get_heroku_connect_field_mapping() == (
            {"Id": {}, "SystemModstamp": {}},
            {"Id": {"unique": True}, "SystemModstamp": {"unique": False}},
            None,
        )

    def test_record_type(self):
        """
        Test ``RecordType`` object edge case.

        See: https://help.heroku.com/sharing/5295ce37-d767-4355-aef7-95f3cde95915
        """

        class RecordType(hc_models.HerokuConnectModel):
            sf_object_name = "RecordType"

            class Meta:
                abstract = True

        assert not any(f.name == "is_deleted" for f in RecordType._meta.fields)
        assert RecordType.get_heroku_connect_field_mapping() == (
            {"Id": {}, "SystemModstamp": {}},
            {"Id": {"unique": True}, "SystemModstamp": {"unique": False}},
            None,
        )

    def test_check_sf_object_name_abstract(self):
        class MyModel(hc_models.HerokuConnectModel):
            class Meta:
                app_label = "test"
                abstract = True

        errors = MyModel.check()
        assert (
            checks.Error(
                'test.MyModel must define a "sf_object_name".',
                id="heroku_connect.E001",
            )
            not in errors
        )

    def test_check_sf_object_name_concrete(self):
        # the check for concrete models breaks when we try to use a
        # temporary `MyClass`, because `model._meta.app_config` is
        # invalid when just definiting `Meta.app_label`.
        # So for this test we just use an existing model and break
        # it.
        setattr(NumberModel, "sf_object_name", None)

        errors = NumberModel.check()
        assert errors == [
            checks.Error(
                'testapp.NumberModel must define a "sf_object_name".',
                id="heroku_connect.E001",
            )
        ]

    def test_check_sf_access(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "Custom_Object__c"
            sf_access = "wrong_value"

            class Meta:
                app_label = "test"
                abstract = True

        errors = MyModel.check()
        assert errors == [
            checks.Error(
                "test.MyModel.sf_access must be one of ['read_only', 'read_write']",
                hint="wrong_value",
                id="heroku_connect.E002",
            )
        ]

    def test_check_unique_sf_field_names(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            date1 = hc_models.DateTime(sf_field_name="Date1__c", db_column="date1")
            date2 = hc_models.DateTime(sf_field_name="Date1__c", db_column="date2")

            class Meta:
                app_label = "test"
                abstract = True

        errors = MyModel.check()
        assert errors == [
            checks.Error(
                "test.MyModel has duplicate Salesforce field names.",
                hint=["Date1__c"],
                id="heroku_connect.E003",
            )
        ]

    def test_check_upsert_field(self):
        class ExternalId(hc_models.HerokuConnectFieldMixin, models.CharField):
            def __init__(self, *args, **kwargs):
                kwargs["max_length"] = 18
                super().__init__(*args, **kwargs)

        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            extId1 = ExternalId(sf_field_name="extId1", upsert=True)
            extId2 = ExternalId(sf_field_name="extId2", upsert=True)

            class Meta:
                app_label = "test"
                abstract = True

        errors = MyModel.check()
        assert errors == [
            checks.Error(
                "test.MyModel can only have a single upsert field.",
                hint=[
                    MyModel._meta.get_field("extId1"),
                    MyModel._meta.get_field("extId2"),
                ],
                id="heroku_connect.E004",
            )
        ]

    def test_check_missing_upsert_field(self):
        class MyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            sf_access = hc_models.READ_WRITE

            class Meta:
                app_label = "test"
                abstract = True

        errors = MyModel.check()
        assert errors == [
            checks.Error(
                "test.MyModel does not have an upsert field.",
                hint="Read-write models need an upsert field.",
                id="heroku_connect.E007",
            )
        ]

    def test_inheritance(self):
        class DateMixin(models.Model):
            date = hc_models.DateTime(sf_field_name="Date__c")

            class Meta:
                app_label = "test"
                abstract = True

        class NameMixin(models.Model):
            name = hc_models.Text(sf_field_name="Name")

            class Meta:
                app_label = "test"
                abstract = True

        class NameDateMixin(DateMixin, NameMixin):
            class Meta:
                app_label = "test"
                abstract = True

        class ChildModel(NameDateMixin, hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            number = hc_models.Number(sf_field_name="Number__c", upsert=True)

            class Meta:
                app_label = "test"

        mapping = ChildModel.get_heroku_connect_mapping()
        assert mapping == {
            "config": {
                "access": "read_only",
                "fields": {
                    "Id": {},
                    "IsDeleted": {},
                    "SystemModstamp": {},
                    "Date__c": {},
                    "Name": {},
                    "Number__c": {},
                },
                "indexes": {
                    "Id": {"unique": True},
                    "SystemModstamp": {"unique": False},
                    "Number__c": {"unique": True},
                },
                "sf_max_daily_api_calls": 30000,
                "sf_notify_enabled": False,
                "sf_polling_seconds": 600,
                "upsert_field": "Number__c",
            },
            "object_name": "My_Object__c",
        }

    def test_qs_methods_on_read_only_model(self):
        class MyReadOnlyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            date = hc_models.DateTime(sf_field_name="Date1__c")

            class Meta:
                app_label = "test"

        data_instance = MyReadOnlyModel(date=timezone.now())
        with pytest.raises(WriteNotSupportedError) as e:
            data_instance.save()
        assert "is a read-only model." in str(e.value)

        data_instance = MyReadOnlyModel(date=timezone.now())
        with pytest.raises(WriteNotSupportedError) as e:
            data_instance.delete()
        assert "is a read-only model." in str(e.value)

    def test_write_methods_on_read_only_model(self):
        class MyReadOnlyModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            date = hc_models.DateTime(sf_field_name="Date1__c")

            class Meta:
                app_label = "test"

        with pytest.raises(WriteNotSupportedError) as e:
            MyReadOnlyModel.objects.update(date=timezone.now())
        assert "is a read-only model." in str(e.value)

        with pytest.raises(WriteNotSupportedError) as e:
            MyReadOnlyModel.objects.all().delete()
        assert "is a read-only model." in str(e.value)

        with pytest.raises(WriteNotSupportedError) as e:
            MyReadOnlyModel.objects.bulk_create([MyReadOnlyModel(date=timezone.now())])
        assert "is a read-only model." in str(e.value)

    def test_multi_table_inheritance(self):
        class HCModel(hc_models.HerokuConnectModel):
            sf_object_name = "My_Object__c"
            sf_access = hc_models.READ_WRITE

            external_id = hc_models.ExternalID(sf_field_name="My_Id__c")

            class Meta:
                app_label = "test"
                abstract = False

        class RegularModel(HCModel):
            hc_model = models.OneToOneField(
                HCModel,
                on_delete=models.CASCADE,
                to_field="external_id",
                parent_link=True,
            )

            class Meta:
                app_label = "test"

        assert RegularModel._meta.managed

        class OtherHCModel(HCModel, hc_models.HerokuConnectModel):
            hc_model = models.OneToOneField(
                HCModel,
                on_delete=models.CASCADE,
                to_field="external_id",
                parent_link=True,
            )

            class Meta:
                app_label = "test"

        assert not OtherHCModel._meta.managed

        class YetAnotherRegularModelMixin(models.Model):
            class Meta:
                app_label = "test"
                abstract = True

        class YetAnotherRegularModel(YetAnotherRegularModelMixin, HCModel):
            hc_model = models.OneToOneField(
                HCModel,
                on_delete=models.CASCADE,
                to_field="external_id",
                parent_link=True,
            )

            class Meta:
                app_label = "test"

        assert YetAnotherRegularModel._meta.managed
