import uuid
from decimal import Decimal

import pytest
import pytz
from django import forms
from django.db import connection, models
from django.utils import timezone

from heroku_connect.db import models as hc_models
from tests.testapp.models import DateTimeModel, NumberModel


def field_factory(field_class, **kwargs):
    kwargs.setdefault('sf_field_name', 'Test_Field__c')

    class TestModel(hc_models.HerokuConnectModel):
        sf_object_name = 'Test__c'
        test_field = field_class(**kwargs)

        class Meta:
            abstract = True

    return TestModel._meta.get_field('test_field')


class TestHerokuConnectFieldMixin:

    def test_db_column(self):
        class MyField(hc_models.HerokuConnectFieldMixin, models.CharField):
            pass

        field = field_factory(MyField, sf_field_name='My_Test_Field__c')
        assert field.db_column == 'my_test_field__c'

    def test_null_default(self):
        class MyField(hc_models.HerokuConnectFieldMixin, models.CharField):
            pass

        field = field_factory(MyField)
        assert field.null is True
        field = field_factory(MyField, null=False)
        assert field.null is False


class TestID:

    def test_max_length(self):
        field = field_factory(hc_models.ID)
        assert field.max_length == 18

        field = field_factory(hc_models.ID, max_length=20)
        assert field.max_length == 18

    def test_unique(self):
        field = field_factory(hc_models.ID)
        assert field.unique is True

        field = field_factory(hc_models.ID, unique=False)
        assert field.unique is False

    def test_editable(self):
        field = field_factory(hc_models.ID)
        assert field.editable is False

        field = field_factory(hc_models.ID, editable=True)
        assert field.editable is False

    def test_null(self):
        field = field_factory(hc_models.ID)
        assert field.null is True

        field = field_factory(hc_models.ID, null=False)
        assert field.null is True


class TestNumber:
    def test_null(self, db):
        n = NumberModel()
        n.save()
        obj = NumberModel.objects.get()
        assert obj.a_number is None

    def test_decimal(self, db):
        n = NumberModel(a_number=Decimal('100.00'))
        n.save()
        with connection.cursor() as c:
            c.execute("SELECT a_number__c FROM number_object__c;")
            assert c.fetchone()[0] == 100.0

        obj = NumberModel.objects.get()
        assert obj.a_number == Decimal('100.00')
        obj = NumberModel.objects.filter(a_number__gt=Decimal('99')).first()
        assert isinstance(obj.a_number, Decimal)


class TestDateTime:
    def test_utc_datetime(self, db):
        datetime_model = DateTimeModel()
        datetime_model.save()

        assert datetime_model.a_datetime is None
        new_york_tz = pytz.timezone("America/New_York")
        now_in_new_york_tz = timezone.now().replace(tzinfo=new_york_tz)
        datetime_model.a_datetime = now_in_new_york_tz
        datetime_model.save()

        datetime_model.refresh_from_db()
        assert timezone.is_aware(datetime_model.a_datetime)
        assert datetime_model.a_datetime == now_in_new_york_tz


class TestExternalID:
    uuid_hex = '653d1c6863404b9689b75fa930c9d0a0'

    def test_null(self, db):
        n = NumberModel(external_id=None)
        n.save()
        obj = NumberModel.objects.get()
        assert obj.external_id is None

    def test_uuid(self, db):
        n = NumberModel()
        n.save()
        with connection.cursor() as c:
            c.execute("SELECT external_id FROM number_object__c;")
            assert c.fetchone()[0] == self.uuid_hex

        obj = NumberModel.objects.get(external_id=self.uuid_hex)
        assert isinstance(obj.external_id, uuid.UUID)
        assert obj.external_id == uuid.UUID(hex=self.uuid_hex)
        obj = NumberModel.objects.get(
            external_id=uuid.UUID(hex=self.uuid_hex))
        assert isinstance(obj.external_id, uuid.UUID)
        assert obj.external_id == uuid.UUID(hex=self.uuid_hex)

    def test_uuid_hex(self, db):
        n = NumberModel(external_id=self.uuid_hex)
        n.save()

        obj = NumberModel.objects.get(
            external_id=uuid.UUID(hex=self.uuid_hex))
        assert isinstance(obj.external_id, uuid.UUID)
        assert obj.external_id == uuid.UUID(hex=self.uuid_hex)


class TestEmail:

    def test_max_length(self):
        field = field_factory(hc_models.Email)
        assert field.max_length == 80

        field = field_factory(hc_models.Email, max_length=42)
        assert field.max_length == 80


class TestPhone:

    def test_max_length(self):
        field = field_factory(hc_models.Phone)
        assert field.max_length == 40

        field = field_factory(hc_models.Phone, max_length=42)
        assert field.max_length == 40


class TestPicklist:

    def test_max_length(self):
        with pytest.raises(KeyError):
            field_factory(hc_models.Picklist)

        choices = (
            ('123', '123'),
            ('12', '12'),
        )
        field = field_factory(hc_models.Picklist, choices=choices)
        assert field.max_length == 255

        choices = (
            ('group1', (
                ('12', '12'),
            )),
            ('group2', (
                ('1', '1'),
                ('123', '123'),
            ),
             ),
        )
        field = field_factory(hc_models.Picklist, choices=choices)
        assert field.max_length == 255

        field = field_factory(hc_models.Picklist, max_length=42, choices=choices)
        assert field.max_length == 42

        field = field_factory(hc_models.Picklist,
                              choices=[(''.join(str(i) for i in range(1000)), 'long option')])
        assert field.max_length == 2890


class TestTextArea:
    def test_max_length(self):
        field = field_factory(hc_models.TextArea)
        assert field.max_length == 255

        field = field_factory(hc_models.TextArea, max_length=42)
        assert field.max_length == 42

    def test_formfield(self):
        field = field_factory(hc_models.TextArea)
        form_field = field.formfield()
        assert type(form_field.widget) == forms.Textarea
        assert form_field.max_length == 255

        choice = (1, 1)
        field = field_factory(hc_models.TextArea, choices=[choice])
        form_field = field.formfield()
        assert type(form_field.widget) == forms.Select
        assert form_field.choices == [('', '---------'), choice]


class TestURL:

    def test_max_length(self):
        field = field_factory(hc_models.URL)
        assert field.max_length == 255

        field = field_factory(hc_models.URL, max_length=42)
        assert field.max_length == 42
