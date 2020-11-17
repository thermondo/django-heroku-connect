import re

import pytest
from django import db
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.test import override_settings

from heroku_connect.models import (
    TRIGGER_LOG_STATE, TriggerLog, TriggerLogArchive
)
from tests.conftest import make_trigger_log, make_trigger_log_for_model


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
        related_trigger_log = make_trigger_log_for_model(connected_model)
        unrelated_trigger_log = make_trigger_log_for_model(connected_class.objects.create())
        trigger_log.save()
        related_trigger_log.save()
        unrelated_trigger_log.save()

        assert set(trigger_log.related()) == {trigger_log, related_trigger_log}
        assert set(trigger_log.related(exclude_self=True)) == {related_trigger_log}

        assert set(unrelated_trigger_log.related()) == {unrelated_trigger_log}
        assert set(unrelated_trigger_log.related(exclude_self=True)) == set()

    def test_capture_update_ok(self, trigger_log, hc_capture_stored_procedures):
        trigger_log.save()
        TriggerLog.objects.get()

        trigger_log.capture_update()

        assert TriggerLog.objects.count() == 2

    def test_capture_update_without_record(self, hc_capture_stored_procedures):
        failed_log = make_trigger_log(
            state=TRIGGER_LOG_STATE['FAILED'],
            table_name='number_object__c',
            record_id=666,
            action='UPDATE',
        )
        failed_log.save()

        with pytest.raises(TriggerLog.DoesNotExist):
            failed_log.capture_update()

    def test_capture_update_wrong_update_field(self, trigger_log, hc_capture_stored_procedures):
        with pytest.raises(FieldDoesNotExist):
            trigger_log.capture_update(update_fields=('NOT A FIELD',))

    def test_capture_insert_ok(self, trigger_log, hc_capture_stored_procedures):
        trigger_log.save()
        TriggerLog.objects.get()

        trigger_log.capture_insert()

        assert TriggerLog.objects.count() == 2

    def test_capture_insert_without_record(self, hc_capture_stored_procedures):
        failed_log = make_trigger_log(
            state=TRIGGER_LOG_STATE['FAILED'],
            table_name='number_object__c',
            record_id=666,
            action='INSERT',
        )
        failed_log.save()

        with pytest.raises(TriggerLog.DoesNotExist):
            failed_log.capture_insert()

    def test_capture_insert_wrong_field(self, trigger_log, hc_capture_stored_procedures):
        with pytest.raises(FieldDoesNotExist):
            trigger_log.capture_insert(exclude_fields=('NOT A FIELD',))

    def test_queryset(self, connected_class, trigger_log, archived_trigger_log):
        trigger_log.save()
        archived_trigger_log.save()
        assert list(TriggerLog.objects.all()) == [trigger_log]
        assert list(TriggerLogArchive.objects.all()) == [archived_trigger_log]

        connected_model = connected_class.objects.create()
        failed = make_trigger_log_for_model(connected_model, state=TRIGGER_LOG_STATE['FAILED'])
        failed.save()
        assert set(TriggerLog.objects.failed()) == {failed}
        assert TriggerLog.objects.all().count() == 2
        assert set(TriggerLog.objects.all()) == {trigger_log, failed}
        assert list(TriggerLogArchive.objects.all()) == [archived_trigger_log]

        related = make_trigger_log_for_model(connected_model)
        related.save()
        assert TriggerLog.objects.related_to(failed).count() == 2
        assert set(TriggerLog.objects.related_to(failed)) == {failed, related}

    def test_str(self, trigger_log, archived_trigger_log):
        assert str(trigger_log)
        assert str(archived_trigger_log)
