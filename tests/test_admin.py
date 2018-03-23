import pytest
from django.contrib.admin import AdminSite
from django.urls import reverse

from heroku_connect import admin
from heroku_connect.models import (
    TRIGGER_LOG_ACTION, TRIGGER_LOG_STATE, TriggerLog, TriggerLogArchive
)
from tests.conftest import make_trigger_log


class TestGenericLogModelAdmin:

    @pytest.fixture
    def admin(self):
        return admin.GenericLogModelAdmin(TriggerLog, AdminSite())

    @pytest.fixture
    def admin_list_url(self):
        route_name = 'admin:{0.app_label}_{0.model_name}'.format(TriggerLog._meta)
        return reverse(route_name + '_changelist')

    def test_table_name_link(self, admin, admin_list_url):
        log = TriggerLog(id=0, table_name='TABLE', record_id=100)
        assert (admin_list_url + '?table_name=TABLE') in admin.table_name_link(log)

    def test_record_id_link(self, admin, admin_list_url):
        log = TriggerLog(id=0, table_name='TABLE', record_id=100)
        assert admin_list_url in admin.record_id_link(log)
        assert 'table_name=TABLE' in admin.record_id_link(log)
        assert 'record_id=100' in admin.record_id_link(log)

    def test_action_label(self, admin):
        log = TriggerLog(id=0, table_name='TABLE', record_id=100,
                         action=TRIGGER_LOG_ACTION['INSERT'])
        assert log.get_action_display() in admin.action_label(log)

    def test_state_label(self, admin):
        log = TriggerLog(id=0, table_name='TABLE', record_id=100,
                         action=TRIGGER_LOG_ACTION['INSERT'])
        assert log.get_state_display() in admin.state_label(log)


@pytest.mark.django_db
class TestAdminActions:

    @staticmethod
    def admin_changelist_url(model):
        return reverse(
            'admin:{meta.app_label}_{meta.model_name}_changelist'.format(meta=model._meta)
        )

    @staticmethod
    def action_post_data(action, queryset):
        return {
            'action': action.__name__,
            '_selected_action': queryset.values_list('pk', flat=True)
        }

    def test_ignore_failed_logs(self, admin_client):
        failed_logs = TriggerLog.objects.bulk_create([
            make_trigger_log(
                state=TRIGGER_LOG_STATE['FAILED'],
                record_id=i,
                action=action,
            )
            for i, action in enumerate(TRIGGER_LOG_ACTION.values())
        ])
        succeeded = make_trigger_log(state=TRIGGER_LOG_STATE['SUCCESS'])
        succeeded.save()

        admin_client.post(
            self.admin_changelist_url(TriggerLog),
            data=self.action_post_data(
                admin.TriggerLogAdmin.ignore_failed_logs_action,
                TriggerLog.objects.all()
            ),
        )

        for failed_log in failed_logs:
            failed_log.refresh_from_db()
            assert failed_log.state == TRIGGER_LOG_STATE['IGNORED']
        succeeded.refresh_from_db()
        assert succeeded.state == TRIGGER_LOG_STATE['SUCCESS']

    def test_retry_failed_logs(self, admin_client):
        failed_logs = TriggerLog.objects.bulk_create([
            make_trigger_log(
                state=TRIGGER_LOG_STATE['FAILED'],
                record_id=i,
                action=action,
            )
            for i, action in enumerate(TRIGGER_LOG_ACTION.values())
        ])
        succeeded = make_trigger_log(state=TRIGGER_LOG_STATE['SUCCESS'])
        succeeded.save()

        admin_client.post(
            self.admin_changelist_url(TriggerLog),
            data=self.action_post_data(
                admin.TriggerLogAdmin.retry_failed_logs_action,
                TriggerLog.objects.all()
            ),
        )

        for failed_log in failed_logs:
            failed_log.refresh_from_db()
            assert failed_log.state == TRIGGER_LOG_STATE['NEW']
        succeeded.refresh_from_db()
        assert succeeded.state == TRIGGER_LOG_STATE['SUCCESS']

    def test_retry_failed_logs_in_archive(self, admin_client):
        failed_logs = TriggerLogArchive.objects.bulk_create([
            make_trigger_log(
                is_archived=True,
                state=TRIGGER_LOG_STATE['FAILED'],
                record_id=i,
                action=action,
            )
            for i, action in enumerate(TRIGGER_LOG_ACTION.values())
        ])
        succeeded = make_trigger_log(is_archived=True, state=TRIGGER_LOG_STATE['SUCCESS'])
        succeeded.save()

        admin_client.post(
            self.admin_changelist_url(TriggerLogArchive),
            data=self.action_post_data(
                admin.TriggerLogAdmin.retry_failed_logs_action,
                TriggerLogArchive.objects.all()
            ),
        )

        for failed_log in failed_logs:
            failed_log.refresh_from_db()
            assert failed_log.state == TRIGGER_LOG_STATE['REQUEUED']
            new_trigger_log = TriggerLog.objects.get(
                table_name=failed_log.table_name,
                record_id=failed_log.record_id,
                action=failed_log.action,
            )
            assert new_trigger_log.state == TRIGGER_LOG_STATE['NEW']
        succeeded.refresh_from_db()
        assert succeeded.state == TRIGGER_LOG_STATE['SUCCESS']
