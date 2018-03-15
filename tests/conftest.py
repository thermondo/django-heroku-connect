import pytest
from django.db import connection
from django.utils import timezone

from heroku_connect.db.models.base import HerokuConnectModel
from heroku_connect.models import (
    TRIGGER_LOG_ACTION, TRIGGER_LOG_STATE, TriggerLog, TriggerLogArchive
)


def make_trigger_log_for_model(model, *, is_archived=False, **kwargs):
    kwargs.setdefault('table_name', model.get_heroku_connect_table_name())
    kwargs.setdefault('record_id', model.id)
    kwargs.setdefault('created_at', timezone.now())
    log = make_trigger_log(is_archived=is_archived, **kwargs)
    return log


def make_trigger_log(*, is_archived, **attrs):
    """
    Make an unsaved trigger log instance from given attributes.

    Returns:
        An unsaved TriggerLog or TriggerLogArchive instance, depending on whether `is_archived`
        is False or True.
    """
    model_cls = TriggerLogArchive if is_archived else TriggerLog
    attrs.setdefault('state', TRIGGER_LOG_STATE['NEW'])
    attrs.setdefault('action', TRIGGER_LOG_ACTION['INSERT'])
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

    # create the model table (let django's test cases roll this back automatically)
    with connection.schema_editor() as editor:
        editor.create_model(cls)

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
def trigger_log(connected_model):
    return make_trigger_log_for_model(connected_model, is_archived=False)


@pytest.fixture()
def archived_trigger_log(connected_model):
    return make_trigger_log_for_model(connected_model, is_archived=True)


@pytest.fixture()
def failed_trigger_log(connected_model):
    return make_trigger_log_for_model(connected_model,
                                      is_archived=False,
                                      state=TRIGGER_LOG_STATE['FAILED'])
