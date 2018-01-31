from itertools import product

import pytest

from heroku_connect.db.models import TriggerLog
from heroku_connect.db.models.errors import (
    ErrorTrack, FixableHerokuModelSyncError, HerokuModelSyncError
)
from tests.testapp.models import NumberModel

from .conftest import create_trigger_log_for_model, reified_models


@pytest.fixture(autouse=True)
def _error_track_table():
    # ErrorTrack table not auto-created with --nomigrations when there's no heroku_connect.models
    # TODO: maybe we should have errors and trigger_log in that very module
    with reified_models(ErrorTrack):
        yield ErrorTrack


@pytest.mark.django_db
class TestErrorTrack:

    def test_from_trigger_log(self, trigger_log):
        track, created = ErrorTrack.objects.get_or_create_for_log(trigger_log, is_initial=True)

        assert created
        assert track.log == trigger_log
        assert track.is_initial

        track2, created = ErrorTrack.objects.get_or_create_for_log(trigger_log, is_initial=False)

        assert not created
        assert track2 == track
        assert track2.log == track.log
        assert track2.is_initial

    def test_without_triggerlog(self, trigger_log):
        track, _ = ErrorTrack.objects.get_or_create_for_log(trigger_log, is_initial=True)
        trigger_log.delete()
        track.refresh_from_db()

        assert track.log is None
        assert list(ErrorTrack.objects.orphaned()) == [track]

    def test_str(self, trigger_log):
        track, _ = ErrorTrack.objects.get_or_create_for_log(trigger_log, is_initial=True)
        assert str(track)


@pytest.mark.django_db
class TestHerokuConnectSyncError:

    def test_attrs(self, trigger_log):
        error = HerokuModelSyncError(trigger_log)

        assert error.args
        assert error.trigger_log == trigger_log
        assert error.model and error.model == trigger_log.get_model()

    def test_iter(self, trigger_log, failed_trigger_log):
        error_list = list(HerokuModelSyncError.iter())

        assert len(error_list) == 1
        assert error_list[0].trigger_log == failed_trigger_log


@pytest.mark.django_db
class TestFixableHerokuModelSyncError:

    @pytest.fixture()
    def known_actions(self):
        return {
            TriggerLog.Action.DELETE,
            TriggerLog.Action.INSERT,
            TriggerLog.Action.UPDATE,
        }

    @pytest.fixture()
    def known_states(self):
        return {
            TriggerLog.State.FAILED,
            TriggerLog.State.NEW,
            TriggerLog.State.IGNORE,
            TriggerLog.State.IGNORED,
            TriggerLog.State.MERGED,
            TriggerLog.State.PENDING,
            TriggerLog.State.READONLY,
            TriggerLog.State.REQUEUE,
            TriggerLog.State.REQUEUED,
            TriggerLog.State.SUCCESS,
        }

    @pytest.mark.parametrize('is_fixable,expected_class', [
        (False, HerokuModelSyncError),
        (True, FixableHerokuModelSyncError),
    ])
    def test_fixable_class_selection(self, is_fixable, expected_class, trigger_log, monkeypatch):
        monkeypatch.setattr(FixableHerokuModelSyncError, 'may_fix', lambda *a: is_fixable)
        error = HerokuModelSyncError(trigger_log)

        assert isinstance(error, HerokuModelSyncError)
        assert type(error) is expected_class

    @pytest.mark.parametrize('action,state', product(
        TriggerLog.Action.values(), TriggerLog.State.values()
    ))
    def test_may_fix_action_state(self, action, state, trigger_log, known_actions, known_states):
        fixable_states = {TriggerLog.State.FAILED}
        fixable_actions = {TriggerLog.Action.INSERT, TriggerLog.Action.UPDATE}
        trigger_log.action = action
        trigger_log.state = state
        may_fix = (action in fixable_actions and state in fixable_states)

        assert action in known_actions
        assert state in known_states
        assert FixableHerokuModelSyncError.may_fix(trigger_log) is may_fix

    def test_may_not_fix_error_tracked_logs(self, failed_trigger_log):
        assert FixableHerokuModelSyncError.may_fix(failed_trigger_log)
        track, _ = ErrorTrack.objects.get_or_create_for_log(failed_trigger_log, is_initial=True)
        assert not FixableHerokuModelSyncError.may_fix(failed_trigger_log)

    @pytest.mark.parametrize('action', [TriggerLog.Action.INSERT, TriggerLog.Action.UPDATE])
    def test_fix(self, action, failed_trigger_log, monkeypatch):
        failed_trigger_log.action = action
        error = HerokuModelSyncError(failed_trigger_log)
        patch_target = {
            TriggerLog.Action.INSERT: 'capture_insert_from_model',
            TriggerLog.Action.UPDATE: 'capture_update_from_model',
        }[action]
        monkeypatch.setattr(TriggerLog, patch_target, lambda *a, **kw: [])

        error.fix()

        assert ErrorTrack.objects.filter(trigger_log_id=failed_trigger_log.id).exists()

    def test_fix_with_delayed_fields(self, create_trigger_log_tables, monkeypatch):
            model = NumberModel.objects.create(a_number=42)
            failed_log = create_trigger_log_for_model(model,
                                                      state=TriggerLog.State.FAILED,
                                                      action=TriggerLog.Action.INSERT)
            error = HerokuModelSyncError(failed_log)
            assert isinstance(error, FixableHerokuModelSyncError)
            new_insert = create_trigger_log_for_model(model, action=TriggerLog.Action.INSERT)
            monkeypatch.setattr(TriggerLog, 'capture_insert_from_model',
                                lambda *a, **kw: [new_insert])
            new_update = create_trigger_log_for_model(model, action=TriggerLog.Action.UPDATE)
            monkeypatch.setattr(TriggerLog, 'capture_update_from_model',
                                lambda *a, **kw: [new_update])

            error.fix(delay_fields=('number',))

            assert ErrorTrack.objects.of_log(failed_log).count() == 1
            assert ErrorTrack.objects.of_log(failed_log).filter(is_initial=True).exists()

            assert ErrorTrack.objects.of_log(new_insert).count() == 1
            assert ErrorTrack.objects.of_log(new_insert).filter(is_initial=False).exists()

            assert ErrorTrack.objects.of_log(new_update).count() == 1
            assert ErrorTrack.objects.of_log(new_update).filter(is_initial=False).exists()

    def test_fix_with_model_update(self, create_trigger_log_tables, monkeypatch):
        monkeypatch.setattr(TriggerLog, 'capture_insert_from_model', lambda *a, **kw: [])
        monkeypatch.setattr(TriggerLog, 'capture_update_from_model', lambda *a, **kw: [])
        model = NumberModel.objects.create(a_number=42)
        failed_log = create_trigger_log_for_model(model, state=TriggerLog.State.FAILED)
        error = FixableHerokuModelSyncError(failed_log)

        error.fix(update_model={'a_number': 43})

        model.refresh_from_db()
        assert model.a_number == 43
