import re

import pytest
from django import db

from heroku_connect.db.models import TriggerLog, TriggerLogArchive
from tests.db.models.conftest import create_trigger_log_for_model


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

    def test_queryset(self, connected_class, trigger_log, archived_trigger_log):
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

        connected_model = connected_class.objects.create()
        failed = create_trigger_log_for_model(connected_model, state=TriggerLog.State.FAILED)

        assert set(TriggerLog.objects.failed()) == {failed}

    def test_str(self, trigger_log, archived_trigger_log):
        assert str(trigger_log)
        assert str(archived_trigger_log)
