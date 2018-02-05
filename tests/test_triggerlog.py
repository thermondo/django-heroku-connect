import re

import pytest
from django import db
from django.core.exceptions import FieldDoesNotExist

from heroku_connect.models import TriggerLog, TriggerLogArchive
from tests.conftest import create_trigger_log_for_model


@pytest.mark.django_db
class TestTriggerLog:

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
        with pytest.raises(FieldDoesNotExist):
            trigger_log.capture_update(update_fields=('NOT A FIELD',))

    def test_capture_insert(self, trigger_log):
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
        failed = create_trigger_log_for_model(connected_model, state=TriggerLog.State.FAILED)
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

    @pytest.mark.parametrize('log1_state', TriggerLog.State.values())
    @pytest.mark.parametrize('log2_state', TriggerLog.State.values())
    @pytest.mark.parametrize('log1_model', [1])
    @pytest.mark.parametrize('log2_model', [1, 2])
    @pytest.mark.parametrize('log1_archived', [False, True])
    @pytest.mark.parametrize('log2_archived', [False, True])
    def test_initial_failures(self,
                              log1_state,
                              log2_state,
                              log1_model,
                              log2_model,
                              log1_archived,
                              log2_archived,
                              connected_class,
                              create_trigger_log_tables):

        logs = []
        models = {
            x: connected_class(id=x) for x in {log1_model, log2_model}
        }
        logs_kwargs = [
            {'state': log1_state, 'model': models[log1_model], 'is_archived': log1_archived},
            {'state': log2_state, 'model': models[log2_model], 'is_archived': log2_archived},
        ]
        for kwargs in logs_kwargs:
            log = create_trigger_log_for_model(**kwargs)
            logs.append(log)
        log1, log2 = logs
        assert log1.id < log2.id

        if TriggerLog.State.FAILED not in {log1.state, log2.state}:
            expected = []
        elif (log1_state, log2_state) == (TriggerLog.State.FAILED, TriggerLog.State.FAILED):
            expected = [log1] if (log1_model == log2_model) else [log1, log2]
        elif log1_state == TriggerLog.State.FAILED:
            expected = [log1]
        elif log2_state == TriggerLog.State.FAILED:
            expected = [log2]
        else:
            assert False, 'Missing check condition: {}'.format(logs_kwargs)
        expected_triggerlog_failures = [l for l in expected if isinstance(l, TriggerLog)]
        expected_archived_failures = [l for l in expected if isinstance(l, TriggerLogArchive)]

        assert list(TriggerLog.objects.initial_failures()) == expected_triggerlog_failures
        assert list(TriggerLogArchive.objects.initial_failures()) == expected_archived_failures
