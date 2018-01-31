from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html

from heroku_connect.models import TriggerLog, TriggerLogArchive


@admin.register(TriggerLog)
class TriggerLogAdmin(admin.ModelAdmin):
    empty_value_display = '<NULL>'

    # LIST
    date_hierarchy = 'created_at'
    list_display = ('created_at', 'action', 'table_name', 'record_id_link', 'sf_message',
                    'state_label',)
    list_filter = ('action', 'state', 'table_name')
    list_per_page = 100
    list_max_show_all = 200
    search_fields = ('record_id', 'sf_id', 'sf_message')

    # DETAIL
    readonly_fields = [field.name for field in TriggerLog._meta.get_fields() if not field.editable]
    save_as = True
    save_on_top = True

    def state_label(self, log):
        state = log.state
        mod = {
            TriggerLog.State.SUCCESS: 'success',
            TriggerLog.State.FAILED: 'danger',
            TriggerLog.State.NEW: 'primary',
            TriggerLog.State.PENDING: 'info',
            TriggerLog.State.REQUEUE: 'warning',
            TriggerLog.State.REQUEUED: 'warning',
        }.get(state, 'default')
        mod2 = {
            TriggerLog.State.FAILED: ' label-important',  # fallback for bootstrap 2
            TriggerLog.State.NEW: ' label-inverse',
        }.get(state, '')
        return format_html('<span class="label label-{mod}{mod2}">{state}</a>',
                           mod=mod, mod2=mod2, state=state)
    state_label.allow_tags = True
    state_label.short_description = 'State'
    state_label.admin_order_field = 'state'

    def record_id_link(self, log):
        if not log.record_id:
            return None
        template = '{record_id}'
        new_url = self._build_filter_url(type(log), log)
        if new_url:
            template += ' <a href="{url}">[filter]</a>'
        return format_html(template, url=new_url, record_id=log.record_id)
    record_id_link.allow_tags = True
    record_id_link.short_description = 'Record ID'
    record_id_link.admin_order_field = 'record_id'

    @classmethod
    def _build_filter_url(cls, model, log):
        table_name, record_id = log.table_name, log.record_id
        if not table_name and record_id:
            return None
        record_query = {
            'table_name__exact': log.table_name,
            'record_id': log.record_id,
        }
        content_type = ContentType.objects.get_for_model(model)
        url = reverse('admin:{app_label}_{model}_changelist'.format(**content_type.__dict__))
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        query.update(record_query)
        parts = parts._replace(query=urlencode(query))
        return urlunsplit(parts)


@admin.register(TriggerLogArchive)
class TriggerLogArchiveAdmin(TriggerLogAdmin):
    pass
