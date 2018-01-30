from itertools import product

import pytest

from heroku_connect.db.models import TriggerLog
from heroku_connect.db.models.errors import (
    ErrorTrack, FixableHerokuModelSyncError, HerokuModelSyncError
)

from .conftest import create_trigger_log_for_model, reified_models


@pytest.fixture(autouse=True)
def _error_track_table():
    # models are not auto-created because there's no heroku_connect.models module
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

    @pytest.mark.parametrize('action,state',
                             product(TriggerLog.Action.values(), TriggerLog.State.values()))
    def test_may_fix_state_action(self, action, state, trigger_log):
        known_states = {
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
        known_actions = {
            TriggerLog.Action.DELETE,
            TriggerLog.Action.INSERT,
            TriggerLog.Action.UPDATE,
        }
        fixable_states = {TriggerLog.State.FAILED}
        fixable_actions = {TriggerLog.Action.INSERT, TriggerLog.Action.UPDATE}

        trigger_log.action = action
        trigger_log.state = state
        may_fix = (action in fixable_actions and state in fixable_states)
        expected_type = (FixableHerokuModelSyncError if may_fix else HerokuModelSyncError)
        assert issubclass(expected_type, HerokuModelSyncError)
        assert action in known_actions
        assert state in known_states
        assert FixableHerokuModelSyncError.may_fix(trigger_log) is may_fix
        assert type(HerokuModelSyncError(trigger_log)) is expected_type

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
