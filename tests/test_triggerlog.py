import re
from collections import namedtuple
from itertools import chain, groupby, product
from operator import attrgetter

import pytest
from django import db
from django.core.exceptions import FieldDoesNotExist

from heroku_connect.models import TriggerLog, TriggerLogArchive
from tests.conftest import create_trigger_log_for_model, make_trigger_log


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


class TestInitialFailure:

    MATRIX = {
        'log1': {
            'state': TriggerLogArchive.State.values(),
            'record_id': [1],
            'table_name': ['TABLE_A'],
            'is_archived': [False, True],
        },
        'log2': {
            'state': TriggerLogArchive.State.values(),
            'record_id': [1, 2],
            'table_name': ['TABLE_A', 'TABLE_B'],
            'is_archived': [False, True],
        },
    }

    class Key(namedtuple('LogTuple', 'id state table_name record_id is_archived')):
        def __new__(cls, trigger_log):
            return super().__new__(cls, *(getattr(trigger_log, name) for name in super()._fields))
        
        def __repr__(self):
            return repr(tuple(self))

    Run = namedtuple('Run', 'id config logs')

    @staticmethod
    def is_related(log1, log2):
        return (log1.table_name, log1.record_id) == (log2.table_name, log2.record_id)

    @classmethod
    def expect_initial_failure(cls, log, logs):
        SUCCESS = TriggerLog.State.SUCCESS
        FAILED = TriggerLog.State.FAILED
        by_id = attrgetter('id')
        by_state = attrgetter('state')
        is_related = cls.is_related
        related_logs = sorted((l for l in logs if is_related(l, log)), key=by_id)
        try:
            index = related_logs.index(log)
        except ValueError:
            index = sorted(related_logs + [log], key=by_id).index(log)
        previous_logs = related_logs[:index]
        previous_by_state = {
            state: list(log_group)  # still sorted by id because `sorted` is stable
            for state, log_group
            in groupby(sorted(previous_logs, key=by_state), key=by_state)
        }
        if log.state != FAILED:
            return False
        if FAILED not in previous_by_state:
            return True
        return (SUCCESS in previous_by_state and
                previous_by_state[SUCCESS][-1].id > previous_by_state[FAILED][-1].id)

    @classmethod
    def make_trigger_log_runs_from_matrix(cls):
        all_values = chain.from_iterable(l.values() for l in cls.MATRIX.values())
        last_id = 0
        runs = []
        for run_id, config in enumerate(product(*all_values), start=1):
            logs = []
            config = iter(config)
            for log_id, attrs in enumerate(cls.MATRIX.values(), start=last_id + 1):
                last_id = log_id
                attrs = {key: next(config) for key in attrs.keys()}
                attrs['table_name'] = '{}_{}'.format(run_id, attrs['table_name'])
                log = make_trigger_log(id=log_id, **attrs)
                logs.append(log)
            runs.append(cls.Run(run_id, config, logs))
        return runs

    @classmethod
    def bulk_create_logs(cls, logs):
        TriggerLog.objects.bulk_create(l for l in logs if isinstance(l, TriggerLog))
        TriggerLogArchive.objects.bulk_create(l for l in logs if isinstance(l, TriggerLogArchive))

    @pytest.mark.django_db
    def test_initial_failure_matrix(self, create_trigger_log_tables):
        key = self.Key
        expect_initial_failure = self.expect_initial_failure
        runs = self.make_trigger_log_runs_from_matrix()
        all_logs = list(chain.from_iterable(run.logs for run in runs))
        self.bulk_create_logs(all_logs)

        actual_initial_failures = {
            key(log): log.is_initial_failure
            for log in chain(TriggerLog.objects.annotate_initial_failures(),
                             TriggerLogArchive.objects.annotate_initial_failures())
        }

        for run in runs:
            diff = {
                k: {
                    'actual': actual,
                    'expect': expect,
                    'logs': logs,
                }
                for k, actual, expect, logs in (
                    (
                        key(log),
                        actual_initial_failures[key(log)],
                        expect_initial_failure(log, run.logs),
                        run.logs,
                    )
                    for log in run.logs
                )
                if actual != expect
            }
            assert not diff
