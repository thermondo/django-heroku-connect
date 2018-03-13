import pytest
from django.contrib.admin import AdminSite
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from heroku_connect.admin import GenericLogModelAdmin
from heroku_connect.models import TRIGGER_LOG_ACTION, TriggerLog


class TestTriggerLogAdmin:

    @pytest.fixture
    def admin(self):
        return GenericLogModelAdmin(TriggerLog, AdminSite())

    @pytest.fixture
    def admin_route_name(self, db):
        content_type = ContentType.objects.get_for_model(TriggerLog)
        return 'admin:{0.app_label}_{0.model}'.format(content_type)

    @pytest.fixture
    def admin_list_url(self, admin_route_name):
        return reverse(admin_route_name + '_changelist')

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
