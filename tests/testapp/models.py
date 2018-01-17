import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from heroku_connect.db import models as hc_models

__all__ = ('NumberModel', 'OtherModel')


def frozen_uuid_generator():
    return uuid.UUID(hex='653d1c6863404b9689b75fa930c9d0a0')


class NumberModel(hc_models.HerokuConnectModel):
    sf_object_name = 'Number_Object__c'

    a_number = hc_models.Number(_('yet another number'), sf_field_name='A_Number__c',
                                max_digits=3, decimal_places=2)
    external_id = hc_models.ExternalID(sf_field_name='External_ID',
                                       default=frozen_uuid_generator, upsert=True)


class OtherModel(models.Model):
    number = models.ForeignKey(NumberModel, on_delete=models.CASCADE)
    other_number = models.ForeignKey('testapp.NumberModel',
                                     on_delete=models.CASCADE, db_constraint=False)
    more_numbers = models.ManyToManyField(NumberModel)


class DateTimeModel(hc_models.HerokuConnectModel):
    sf_object_name = 'DateTime_Object__c'

    a_datetime = hc_models.DateTime(_('a date time field'), sf_field_name='A_DateTime__c')
