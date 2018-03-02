import re

import pytest
from django import db
from django.core.exceptions import FieldDoesNotExist

from heroku_connect.models import (
    TRIGGER_LOG_STATE, TriggerLog, TriggerLogArchive, TriggerLogPermanent
)
from tests.conftest import create_trigger_log_for_model


@pytest.mark.django_db
class TestTriggerLog:

    @pytest.fixture()
    def _hstore_extension(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS HSTORE;')

    def test_is_archived(self, archived_trigger_log, trigger_log):
        assert archived_trigger_log.is_archived is True
        assert trigger_log.is_archived is False

    def test_get_model(self, trigger_log, connected_model):
        assert trigger_log.get_model() == connected_model
        connected_model.delete()
        assert trigger_log.get_model() is None

    def test_related(self, connected_class, connected_model, trigger_log):
        related_trigger_log = create_trigger_log_for_model(connected_model)
        unrelated_trigger_log = create_trigger_log_for_model(connected_class.objects.create())

        assert set(trigger_log.related()) == {trigger_log, related_trigger_log}
        assert set(trigger_log.related(exclude_self=True)) == {related_trigger_log}

        assert set(unrelated_trigger_log.related()) == {unrelated_trigger_log}
        assert set(unrelated_trigger_log.related(exclude_self=True)) == set()

    def test_capture_update(self, trigger_log, _hstore_extension):
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
        with pytest.raises(FieldDoesNotExist):
            trigger_log.capture_update(update_fields=('NOT A FIELD',))

    def test_capture_insert(self, trigger_log, _hstore_extension):
        with pytest.raises(db.ProgrammingError):
            try:
                exclude_fields = ['_hc_lastop', '_hc_err']  # for test coverage
                trigger_log.capture_insert(exclude_fields=exclude_fields)
            except db.ProgrammingError as error:
                regex = 'function {schema}hc_capture_insert_from_row{args} does not exist'.format(
                    schema=r'(?:[^.]+\.)?',
                    args=re.escape('(hstore, unknown, text[])')
                )
                assert re.search(regex, str(error))
                raise
        with pytest.raises(FieldDoesNotExist):
            trigger_log.capture_insert(exclude_fields=('NOT A FIELD',))

    def test_queryset(self, connected_class, trigger_log, archived_trigger_log):
        assert list(TriggerLog.objects.all()) == [trigger_log]
        assert list(TriggerLogArchive.objects.all()) == [archived_trigger_log]

        connected_model = connected_class.objects.create()
        failed = create_trigger_log_for_model(connected_model, state=TRIGGER_LOG_STATE['FAILED'])
        assert set(TriggerLog.objects.failed()) == {failed}
        assert TriggerLog.objects.all().count() == 2
        assert set(TriggerLog.objects.all()) == {trigger_log, failed}
        assert list(TriggerLogArchive.objects.all()) == [archived_trigger_log]

        related = create_trigger_log_for_model(connected_model)
        assert TriggerLog.objects.related_to(failed).count() == 2
        assert set(TriggerLog.objects.related_to(failed)) == {failed, related}

    def test_str(self, trigger_log, archived_trigger_log):
        assert str(trigger_log)
        assert str(archived_trigger_log)


@pytest.mark.django_db
class TestTriggerLogPermanent:

    def test_create_unknown(self, trigger_log, archived_trigger_log, failed_trigger_log):
        original_logs = [trigger_log, archived_trigger_log, failed_trigger_log]

        def fields_dict(instance):
            return {
                name: getattr(instance, name)
                for name in (f.name for f in instance._meta.get_fields())
            }

        TriggerLogPermanent.create_unknown(original_logs)
        assert TriggerLogPermanent.objects.count() == len(original_logs)
        for original_log in original_logs:
            created = TriggerLogPermanent.objects.get(id=original_log.id)
            assert fields_dict(created) == fields_dict(original_log)

        TriggerLogPermanent.create_unknown(original_logs)
        assert TriggerLogPermanent.objects.count() == len(original_logs)

    def test_related_surrounding(self):
        SUCCESS, FAILED = TRIGGER_LOG_STATE['SUCCESS'], TRIGGER_LOG_STATE['FAILED']
        id_states = [
            (0, SUCCESS), (1, SUCCESS), (2, SUCCESS), (3, FAILED), (4, FAILED)
        ]
        logs = TriggerLogPermanent.objects.bulk_create([
            TriggerLogPermanent(id=i, state=state, table_name='TABLE', record_id='111')
            for i, state, in id_states
        ])
        unrelated_log = TriggerLogPermanent.objects.create(
            id=len(logs),
            state=FAILED,
            table_name='TABLE',
            record_id='666',
        )

        assert list(logs[0].related_surrounding().values_list('id', 'state')) == id_states[:2]
        assert list(logs[1].related_surrounding().values_list('id', 'state')) == id_states[:3]
        assert list(logs[2].related_surrounding().values_list('id', 'state')) == id_states[1:]
        assert list(logs[3].related_surrounding().values_list('id', 'state')) == id_states[2:]
        assert list(logs[4].related_surrounding().values_list('id', 'state')) == id_states[2:]
        assert list(unrelated_log.related_surrounding()) == [unrelated_log]
