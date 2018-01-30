import pytest

from heroku_connect.db.models.errors import ErrorTrack, HerokuModelSyncError

from .conftest import reified_models


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
