import pytest
from django.contrib.admin import AdminSite
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from heroku_connect.admin import TriggerLogPermanentAdmin
from heroku_connect.models import TriggerLogPermanent


class TestTriggerLogPermanentAdmin:

    @pytest.fixture
    def admin(self):
        return TriggerLogPermanentAdmin(TriggerLogPermanent, AdminSite())

    @pytest.fixture
    def admin_route_name(self, db):
        content_type = ContentType.objects.get_for_model(TriggerLogPermanent)
        return 'admin:{0.app_label}_{0.model}'.format(content_type)

    @pytest.fixture
    def admin_list_url(self, admin_route_name):
        return reverse(admin_route_name + '_changelist')

    def test_table_name_link(self, admin, admin_list_url):
        log = TriggerLogPermanent(id=0, table_name='TABLE', record_id=100)
        assert (admin_list_url + '?table_name=TABLE') in admin.table_name_link(log)

    def test_record_id_link(self, admin, admin_list_url):
        log = TriggerLogPermanent(id=0, table_name='TABLE', record_id=100)
        assert admin_list_url in admin.record_id_link(log)
        assert 'table_name=TABLE' in admin.record_id_link(log)
        assert 'record_id=100' in admin.record_id_link(log)

    def test_action_label(self, admin):
        log = TriggerLogPermanent(id=0, table_name='TABLE', record_id=100,
                                  action=TriggerLogPermanent.Action.INSERT)
        assert log.get_action_display() in admin.action_label(log)

    def test_state_label(self, admin):
        log = TriggerLogPermanent(id=0, table_name='TABLE', record_id=100,
                                  action=TriggerLogPermanent.Action.INSERT)
        assert log.get_state_display() in admin.state_label(log)

    def test_related_logs(self, admin, db):
        logs = TriggerLogPermanent.objects.bulk_create([
            TriggerLogPermanent(id=12345, table_name='TABLE', record_id=100),
            TriggerLogPermanent(id=54321, table_name='TABLE', record_id=100),
        ])
        assert '12345' in admin.related_logs(logs[0])
        assert '54321' in admin.related_logs(logs[0])
