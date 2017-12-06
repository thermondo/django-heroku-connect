import uuid
from contextlib import contextmanager

from django.db import connection
from django.utils.translation import ugettext_lazy as _

from heroku_connect import models
from heroku_connect.utils import get_heroku_connect_models

__all__ = ('NumberModel',)


def frozen_uuid_generator():
    return uuid.UUID(hex='653d1c6863404b9689b75fa930c9d0a0')


class NumberModel(models.HerokuConnectModel):
    sf_object_name = 'Number_Object__c'

    a_number = models.Number(_('yet another number'), sf_field_name='A_Number__c',
                             max_digits=3, decimal_places=2)
    external_id = models.ExternalID(sf_field_name='External_ID',
                                    default=frozen_uuid_generator, upsert=True)

    _sql = """
CREATE TABLE number_object__c (
    id integer NOT NULL,
    sfid character varying(18),
    isdeleted boolean,
    systemmodstamp timestamp without time zone,
    a_number__c double precision,
    external_id character varying(32),
    _hc_lastop character varying(32),
    _hc_err text
);

CREATE UNIQUE INDEX number_object__c_external_id
    ON number_object__c USING btree (external_id);

CREATE SEQUENCE number_object__c_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE ONLY number_object__c
    ADD CONSTRAINT number_object__c_pkey PRIMARY KEY (id);

ALTER SEQUENCE number_object__c_id_seq OWNED BY number_object__c.id;

ALTER TABLE ONLY number_object__c ALTER COLUMN id
    SET DEFAULT nextval('number_object__c_id_seq'::regclass);
"""


@contextmanager
def heroku_connect_schema():
    with connection.cursor() as cursor:
        cursor.execute("""
        CREATE SCHEMA IF NOT EXISTS salesforce;
        SET search_path = salesforce, pg_catalog;
        """)
        test_models = filter(lambda x: hasattr(x, '_sql'), get_heroku_connect_models())
        for model in test_models:
            cursor.execute(model._sql)
        yield
        cursor.execute("DROP SCHEMA IF EXISTS salesforce CASCADE;")
