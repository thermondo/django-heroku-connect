"""
Salesforce fields for Django's ORM.

You can find a list of all Salesforce fields mapped to PostgreSQL here.
See Heroku Connect's `mapped data types`_.

.. _`mapped data types`:
    https://devcenter.heroku.com/articles/heroku-connect-database-tables#mapped-data-types

"""
import uuid

from django.db import models

__all__ = (
    'HerokuConnectFieldMixin', 'AnyType', 'ID', 'Checkbox', 'Currency',
    'Date', 'DateTime', 'Email', 'EncryptedString', 'Number', 'Percent',
    'Phone', 'Picklist', 'Text', 'TextArea', 'Time', 'URL', 'ExternalID',
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
        kwargs['unique'] = True
        kwargs['editable'] = False
        kwargs['null'] = False
        super().__init__(*args, **kwargs)


class ExternalID(HerokuConnectFieldMixin, models.UUIDField):
    """
    External ID field for Salesforce objects.

    This field uses `uuid.uuid4` as a default UUID function.
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

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)


class Checkbox(HerokuConnectFieldMixin, models.NullBooleanField):
    """Salesforce ``Checkbox`` field."""

    pass


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

    def from_db_value(self, value, expression, connection, context):
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
    """Salesforce ``DateTime`` field."""

    pass


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
        kwargs['max_length'] = max_length
        super().__init__(*args, **kwargs)


class Text(HerokuConnectFieldMixin, models.CharField):
    """Salesforce ``Text`` field."""

    pass


class TextArea(HerokuConnectFieldMixin, models.TextField):
    """Salesforce ``TextArea`` field, both ``long`` and ``rich``."""

    pass


class Time(HerokuConnectFieldMixin, models.TimeField):
    """Salesforce ``Time`` field."""

    pass


class URL(HerokuConnectFieldMixin, models.URLField):
    """Salesforce ``URL`` field."""

    pass
