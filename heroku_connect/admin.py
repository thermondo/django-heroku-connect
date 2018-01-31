from django.contrib import admin
from django.utils.html import format_html

from heroku_connect.models import TriggerLog


@admin.register(TriggerLog)
class TriggerLogAdmin(admin.ModelAdmin):
    empty_value_display = '<NULL>'

    # LIST
    date_hierarchy = 'created_at'
    list_display = ('created_at', 'action', 'table_name', 'record_id', 'sf_message', 'state_label',)
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
