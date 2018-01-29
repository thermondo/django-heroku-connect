import re
from contextlib import contextmanager

import pytest
from django import db
from django.db import connection

from heroku_connect.db.models import (
    HerokuConnectModel, HerokuConnectModelBase, TriggerLog, TriggerLogArchive
)


@contextmanager
def reified_models(model_class, *model_classes):
    """Create a model's table in the database.

    This is useful for testing unmanaged models, or ones defined after Django setup already
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
def _create_trigger_log_tables():
    # Need to create the tables manually as the models are `managed = False`.
    model_classes = (TriggerLog, TriggerLogArchive)
    with reified_models(*model_classes):
        yield


def _create_trigger_log_for_model(model, *, is_archived=False, **kwargs):
    model_cls = TriggerLogArchive if is_archived else TriggerLog
    kwargs.setdefault('table_name', HerokuConnectModelBase.get_table_name_for_class(type(model)))
    kwargs.setdefault('record_id', model.id)
    kwargs.setdefault('state', TriggerLog.State.NEW)
    kwargs.setdefault('action', TriggerLog.Action.INSERT)
    return model_cls.objects.create(**kwargs)


@pytest.fixture()
def connected_class():
    """Get a HerokuConnectedModel subclass"""
    # TODO find out what's going on with the django model registry =:-O
    # For some reason, defining the class in module namespace keeps it in the Django model registry
    # (apps.all_models()), while it does not remain registered when defined here.
    # We want to keep the registry clean, but still have a non-abstract model class with a manager
    # and all...
    global __ConnectedTestModel
    try:
        cls = __ConnectedTestModel
    except NameError:
        # define the class only once, or the django app registry will warn about redefining models
        class ConnectedTestModel(HerokuConnectModel):
            sf_object_name = 'CONNECTED_TEST_MODEL'

            class Meta:
                app_label = 'tests'
        cls = __ConnectedTestModel = ConnectedTestModel
    with reified_models(cls):
        yield cls


@pytest.fixture()
def model(connected_class):
    return connected_class.objects.create()


@pytest.fixture()
def trigger_log(_create_trigger_log_tables, model):
    return _create_trigger_log_for_model(model, is_archived=False)


@pytest.fixture()
def archived_trigger_log(_create_trigger_log_tables, model):
    return _create_trigger_log_for_model(model, is_archived=True)


@pytest.mark.django_db
class TestTriggerLog:

    def test_is_archived(self, archived_trigger_log, trigger_log):
        assert archived_trigger_log.is_archived is True
        assert trigger_log.is_archived is False

    def test_get_model(self, trigger_log, model):
        assert trigger_log.get_model() == model
        model.delete()
        assert trigger_log.get_model() is None

    def test_related(self, connected_class, model, trigger_log):
        related_trigger_log = _create_trigger_log_for_model(model)
        unrelated_trigger_log = _create_trigger_log_for_model(connected_class.objects.create())

        assert set(trigger_log.related()) == {trigger_log, related_trigger_log}
        assert set(trigger_log.related(exclude_self=True)) == {related_trigger_log}

        assert set(unrelated_trigger_log.related()) == {unrelated_trigger_log}
        assert set(unrelated_trigger_log.related(exclude_self=True)) == set()

    def test_capture_update(self, trigger_log):
        with pytest.raises(db.ProgrammingError):
            try:
                trigger_log.capture_update()
            except db.ProgrammingError as error:
                regex = 'function {schema}hc_capture_update_from_row{args} does not exist'.format(
                    schema=r'(?:[^.]+\.)?',
                    args=re.escape('(hstore, unknown, text[])')
                )
                assert re.search(regex, str(error))
                raise

    def test_capture_insert(self, trigger_log):
        with pytest.raises(db.ProgrammingError):
            try:
                trigger_log.capture_insert()
            except db.ProgrammingError as error:
                regex = 'function {schema}hc_capture_insert_from_row{args} does not exist'.format(
                    schema=r'(?:[^.]+\.)?',
                    args=re.escape('(hstore, unknown, text[])')
                )
                assert re.search(regex, str(error))
                raise

    def test_queryset(self, trigger_log, archived_trigger_log):
        no_archived = TriggerLog.objects.all()
        is_archived = TriggerLogArchive.objects.all()

        assert trigger_log in no_archived
        assert trigger_log not in is_archived
        assert trigger_log in is_archived.combined()

        assert archived_trigger_log not in no_archived
        assert archived_trigger_log in is_archived
        assert archived_trigger_log in is_archived.combined()

        assert set(no_archived) == set(is_archived.current())
        assert set(no_archived) == set(no_archived.current())
        assert set(is_archived) == set(no_archived.archived())
        assert set(is_archived) == set(is_archived.archived())
        assert set(no_archived.combined()) == set(is_archived.combined())
