from contextlib import contextmanager

import pytest
from django.db import connection
from django.db.models import Max
from django.db.models.functions import Coalesce

from heroku_connect.db.models.base import HerokuConnectModel, registry
from heroku_connect.models import TriggerLog, TriggerLogArchive


@contextmanager
def reified_models(model_class, *model_classes):
    """Create a model's table in the database.

    This is useful for testing un-managed models, or ones defined after Django setup already
    created the tables for the models it knew back then.
    """
    model_classes = (model_class,) + model_classes

    with connection.schema_editor() as schema:
        for cls in model_classes:
            schema.create_model(cls)
    yield
    # let django TestCase transaction rollback take care of cleaning this up again
    #
    # ...or, to explicitly clean up:
    # try:
    #     yield
    # finally:
    #     try:
    #         with connection.schema_editor() as schema:
    #             for cls in created:
    #                 schema.delete_model(cls)
    #     except db.DatabaseError as error:
    #         if 'current transaction is aborted' in str(error):
    #             # We're in a transaction which is rolling back; no need to do our cleanup
    #             pass
    #         else:
    #             raise


@pytest.fixture()
def create_trigger_log_tables():
    # Need to create the tables manually as the models are `managed = False`.
    model_classes = (TriggerLog, TriggerLogArchive)
    with reified_models(*model_classes):
        yield


def create_trigger_log_for_model(model, *, is_archived=False, **kwargs):
    kwargs.setdefault('table_name', registry.get_table_name_for_class(type(model)))
    kwargs.setdefault('record_id', model.id)
    log = make_trigger_log(is_archived=is_archived, **kwargs)
    log.save()
    return log


def make_trigger_log(*, is_archived, **attrs):
    model_cls = TriggerLogArchive if is_archived else TriggerLog
    if 'id' not in attrs:
        max_id = max(
            TriggerLog.objects.aggregate(max=Coalesce(Max('id'), 0))['max'],
            TriggerLogArchive.objects.aggregate(max=Coalesce(Max('id'), 0))['max'],
        )
        attrs['id'] = max_id + 1
    attrs.setdefault('state', TriggerLog.State.NEW)
    attrs.setdefault('action', TriggerLog.Action.INSERT)
    return model_cls(**attrs)



@pytest.fixture()
def connected_class():
    """Get a HerokuConnectedModel subclass"""
    # The class definition is hidden in a fixture to keep the app registry and database table space
    # clean for other tests.
    global __ConnectedTestModel
    try:
        cls = __ConnectedTestModel
        meta = cls._meta
        meta.apps.register_model(meta.app_label, cls)
    except NameError:
        # define the class only once, or django will warn about redefining models
        class ConnectedTestModel(HerokuConnectModel):
            sf_object_name = 'CONNECTED_TEST_MODEL'

            class Meta:
                app_label = 'tests'

        cls = __ConnectedTestModel = ConnectedTestModel
        meta = cls._meta
        # creating the class automatically registers it
    with reified_models(cls):
        try:
            yield cls  # run test
        finally:
            # de-register class from Apps registry
            testapp_models = meta.apps.all_models.get(meta.app_label, {})
            registered_name = None
            for name, model_cls in testapp_models.items():
                if model_cls is cls:
                    registered_name = name
            if registered_name:
                del testapp_models[registered_name]


@pytest.fixture()
def connected_model(connected_class):
    return connected_class.objects.create()


@pytest.fixture()
def trigger_log(create_trigger_log_tables, connected_model):
    return create_trigger_log_for_model(connected_model, is_archived=False)


@pytest.fixture()
def archived_trigger_log(create_trigger_log_tables, connected_model):
    return create_trigger_log_for_model(connected_model, is_archived=True)


@pytest.fixture()
def failed_trigger_log(create_trigger_log_tables, connected_model):
    return create_trigger_log_for_model(connected_model,
                                        is_archived=False,
                                        state=TriggerLog.State.FAILED)
