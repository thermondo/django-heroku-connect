"""
Salesforce fields for Django's ORM.

You can find a list of all Salesforce fields mapped to PostgreSQL here.
See Heroku Connect's `mapped data types`_.

.. _`mapped data types`:
    https://devcenter.heroku.com/articles/heroku-connect-database-tables#mapped-data-types

"""
import uuid

from django import forms
from django.db import models
from django.utils import timezone

__all__ = (
    'HerokuConnectFieldMixin', 'AnyType', 'ID', 'ExternalID', 'Checkbox', 'Number', 'Currency',
    'Date', 'DateTime', 'Email', 'EncryptedString', 'Percent',
    'Phone', 'Picklist', 'Text', 'TextArea', 'TextAreaLong', 'Time', 'URL',
)


class HerokuConnectFieldMixin:
    """Base mixin for Heroku Connect fields."""

    #: (str): Field's Salesforce API name.
    sf_field_name = None
    #: (bool): Whether or not a field is an ``externalId``.
    upsert = False

    def __init__(self, *args, **kwargs):
        self.sf_field_name = kwargs.pop('sf_field_name')
        kwargs.setdefault('db_column', self.sf_field_name.lower())
        kwargs.setdefault('null', True)
        self.upsert = kwargs.pop('upsert', False)
        if self.upsert:
            kwargs.update({
                'unique': True,
                'db_index': True,
            })
        super().__init__(*args, **kwargs)
        if self.unique:
            # unique fields must be indexed in Heroku Connect
            self.db_index = True

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['sf_field_name'] = self.sf_field_name
        kwargs['upsert'] = self.upsert
        return name, path, args, kwargs


class AnyType(HerokuConnectFieldMixin, models.TextField):
    """Salesforce ``AnyType`` field."""

    pass


class ID(HerokuConnectFieldMixin, models.CharField):
    """Salesforce ``ID`` field."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 18
        kwargs['editable'] = False
        kwargs['null'] = True
        kwargs.setdefault('unique', True)
        super().__init__(*args, **kwargs)


class ExternalID(HerokuConnectFieldMixin, models.UUIDField):
    """
    External ID field for Salesforce objects.

    This field uses `uuid.uuid4` as a default UUID function.

    The corresponding field in Salesforce must be type ``Text(32)``.
    In Salesforce it will display the UUID as a HEX. It should be set
    as ``External ID`` as well as ``unique`` (case insensitive).

    The field should only be required on Salesforce if you want to insert
    new records only in your application.

    Note:
        Django does not use Database defaults, should you create new records
        on Salesforce, you need to make sure Salesforce inserts UUIDs or
        handle empty External ID fields in your Django application.

    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('upsert', True)
        kwargs.setdefault('default', uuid.uuid4)
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = self.to_python(value)
        return value.hex

    def from_db_value(self, value, *args, **kwargs):
        return self.to_python(value)


class Checkbox(HerokuConnectFieldMixin, models.BooleanField):
    """Salesforce ``Checkbox`` field."""

    def __init__(self, *args, **kwargs):
        kwargs['null'] = True
        super().__init__(*args, **kwargs)


class Number(HerokuConnectFieldMixin, models.DecimalField):
    """
    Salesforce ``Number`` field.

    Allows users to enter any number. Leading zeros are removed.

    Numbers in Salesforce are constrained by length and decimal places.
    Heroku Connect maps those decimal values to ``double precision``
    floats. To have the same accuracy and avoid Salesforce validation
    rule issues this field uses :obj:`.Decimal` values and casts them
    to floats when persisting them to PostgreSQL.
    """

    def get_internal_type(self):
        return 'FloatField'

    def get_db_prep_save(self, value, connection):
        if value is not None:
            value = float(self.to_python(value))
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is not None:
            value = float(self.to_python(value))
        return value

    def from_db_value(self, value, *args, **kwargs):
        return self.to_python(value)


class Currency(Number):
    """
    Salesforce ``Currency`` field.

    This is used for the money value. On the Salesforce side, the actual
    currency is specified in a ``CurrencyIsoCode`` field
    (see `Currency Field Type`_), which is however (currently) not mapped by
    Heroku Connect.

    .. _`Currency Field Type`:
        https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/field_types.htm#i1435541
    """

    pass


class Date(HerokuConnectFieldMixin, models.DateField):
    """Salesforce ``Date`` field."""

    pass


class DateTime(HerokuConnectFieldMixin, models.DateTimeField):
    """
    Salesforce ``DateTime`` field.

    Heroku connect create tables with time stamp fields but without time zones, and when it syncs
    to Salesforce it treats them as UTC. This field will be always making sure that the dates are
    aware and UTC.
    """

    def db_type(self, connection):
        return 'timestamp without time zone'

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return value
        else:
            return timezone.make_aware(value, timezone.utc)


class Email(HerokuConnectFieldMixin, models.EmailField):
    """Salesforce ``Email`` field."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 80
        super().__init__(*args, **kwargs)


class EncryptedString(HerokuConnectFieldMixin, models.CharField):
    """
    Salesforce ``EncryptedString`` field.

    From the `Heroku Connect doc`_:

        If the user credentials used to authorize Heroku Connect with
        Salesforce don’t have View Encrypted Data permission, then encrypted
        strings will be received from Salesforce in masked format.

        It is possible to update the database with a new plain text value and
        Salesforce will take care of encryption when the new data is pushed
        from the database. The plain text value in the database will be
        overwritten with the masked format when the record is next updated with
        data from Salesforce.

    .. _`Heroku Connect doc`:
        https://devcenter.heroku.com/articles/heroku-connect-database-tables#encrypted-strings
    """

    pass


class Percent(Number):
    """Salesforce ``Percent`` field."""

    pass


class Phone(HerokuConnectFieldMixin, models.CharField):
    """Salesforce ``Phone`` field."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 40
        super().__init__(*args, **kwargs)


class Picklist(HerokuConnectFieldMixin, models.CharField):
    """Salesforce ``Picklist`` field."""

    def __init__(self, *args, **kwargs):
        self.choices = kwargs['choices']
        longest_choice = max(self.flatchoices, key=lambda choice: len(choice[0]))
        max_length = len(longest_choice[0])
        max_length = max(255, max_length)
        kwargs.setdefault('max_length', max_length)
        super().__init__(*args, **kwargs)


class Text(HerokuConnectFieldMixin, models.CharField):
    """Salesforce ``Text`` field."""

    pass


class TextArea(HerokuConnectFieldMixin, models.CharField):
    """Salesforce ``Text Area`` field."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        # Passing max_length to forms.CharField means that the value's length
        # will be validated twice. This is considered acceptable since we want
        # the value in the form field (to pass into widget for example).
        defaults = {'max_length': self.max_length}
        if not self.choices:
            defaults['widget'] = forms.Textarea
        defaults.update(kwargs)
        return super().formfield(**defaults)


class TextAreaLong(HerokuConnectFieldMixin, models.TextField):
    """Salesforce ``Text Area (Long)`` and ``Text Area (Rich)`` field."""

    pass


class Time(HerokuConnectFieldMixin, models.TimeField):
    """Salesforce ``Time`` field."""

    pass


class URL(HerokuConnectFieldMixin, models.URLField):
    """Salesforce ``URL`` field."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        super().__init__(*args, **kwargs)
