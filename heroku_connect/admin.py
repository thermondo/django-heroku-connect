from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.contrib import admin
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from heroku_connect.models import (
    TRIGGER_LOG_STATE, TriggerLog, TriggerLogArchive
)


def _replaced(__values, **__replacements):
    """
    Replace elements in iterable with values from an alias dict, suppressing empty values.

    Used to consistently enhance how certain fields are displayed in list and detail pages.
    """
    return tuple(o for o in (__replacements.get(name, name) for name in __values) if o)


def _get_admin_route_name(model_or_instance):
    """
    Get the base name of the admin route for a model or model instance.

    For use with :func:`django.urls.reverse`, although it still needs the specific route suffix
    appended, for example ``_changelist``.
    """
    model = model_or_instance if isinstance(model_or_instance, type) else type(model_or_instance)
    return 'admin:{meta.app_label}_{meta.model_name}'.format(meta=model._meta)


def _build_admin_filter_url(model, filters):
    """Build a filter URL to an admin changelist of all objects with similar field values."""
    url = reverse(_get_admin_route_name(model) + '_changelist')
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    query.update(filters)
    parts_with_filter = parts._replace(query=urlencode(query))
    return urlunsplit(parts_with_filter)


def _make_admin_link_to_similar(primary_field, *fields, name=None):
    """Create a function that links to a changelist of all objects with similar field values."""
    fields = (primary_field,) + fields
    url_template = '<a href="{url}">{name_or_value}</a>'

    def field_link(self, obj):
        value = getattr(obj, primary_field, None)
        name_or_value = name or value
        filters = {field_name: getattr(obj, field_name) for field_name in fields}
        url = _build_admin_filter_url(obj, filters)
        return format_html(url_template, **locals()) if url else value
    field_link.allow_tags = True
    field_link.short_description = primary_field.replace('_', ' ').capitalize()
    field_link.admin_order_field = primary_field
    field_link.__name__ = field_link.__name__.replace('field', primary_field)

    return field_link


def _ignore_failed_logs(queryset):
    failed_logs = queryset.filter(state=TRIGGER_LOG_STATE['FAILED'])
    return failed_logs.update(state=TRIGGER_LOG_STATE['IGNORED'])


@transaction.atomic
def _retry_failed_log(failed_trigger_log):
    """
    Try to re-apply a failed trigger log action.

    Makes sure the argument trigger log is in a FAILED state and acquires a row lock on it.

    Returns:
          True if the operation succeeded

    """
    model = type(failed_trigger_log)
    try:
        failed_trigger_log = (
            model.objects
            .select_for_update()
            .get(
                id=failed_trigger_log.id,
                state=TRIGGER_LOG_STATE['FAILED'],
            )
        )
    except model.DoesNotExist:
        return False
    failed_trigger_log.redo()
    return True


class GenericLogModelAdmin(admin.ModelAdmin):
    empty_value_display = '<NULL>'

    field_overrides = {
        'action': 'action_label',
        'state': 'state_label',
        'record_id': 'record_id_link',
        'table_name': 'table_name_link'
    }

    # LIST
    date_hierarchy = 'created_at'
    list_display = _replaced(
        ('created_at', 'action', 'table_name', 'record_id', 'sf_message', 'state'),
        **field_overrides)
    list_filter = ('action', 'state', 'table_name')
    list_per_page = 100
    list_max_show_all = 200
    ordering = ('-id',)
    search_fields = ('record_id', 'sf_id', 'sf_message')

    # DETAIL
    readonly_fields = _replaced(
        [field.name for field in TriggerLog._meta.get_fields() if not field.editable],
        **field_overrides)
    save_as = True
    save_on_top = True

    table_name_link = _make_admin_link_to_similar('table_name')
    record_id_link = _make_admin_link_to_similar('record_id', 'table_name')

    def action_label(self, log):
        action = log.action
        return format_html('<span class="label label-default">{action}</span>', action=action)
    action_label.allow_tags = True
    action_label.short_description = 'Action'  # untranslated: is column name in trigger log table
    action_label.admin_order_field = 'action'

    def state_label(self, log):
        state = log.state
        css_label_class = {
            TRIGGER_LOG_STATE['SUCCESS']: 'success',
            TRIGGER_LOG_STATE['FAILED']: 'danger label-important',  # fallback for bootstrap 2
            TRIGGER_LOG_STATE['NEW']: 'primary label-inverse',  # fallback for bootstrap 2
            TRIGGER_LOG_STATE['PENDING']: 'info',
            TRIGGER_LOG_STATE['REQUEUE']: 'warning',
            TRIGGER_LOG_STATE['REQUEUED']: 'warning',
        }.get(state, 'default')
        return format_html('<span class="label label-{css_label_class}">{state}</a>',
                           css_label_class=css_label_class,
                           state=state)
    state_label.allow_tags = True
    state_label.short_description = 'State'  # untranslated: is column name in trigger log table
    state_label.admin_order_field = 'state'


class TriggerLogAdmin(GenericLogModelAdmin):
    actions = ['ignore_failed_logs_action', 'retry_failed_logs_action']
    actions_on_top = True
    actions_on_bottom = True

    def ignore_failed_logs_action(self, request, queryset):
        """Set FAILED trigger logs in queryset to IGNORED."""
        count = _ignore_failed_logs(queryset)
        self.message_user(
            request,
            _('{count} failed trigger logs marked as ignored.').format(count=count),
        )
    ignore_failed_logs_action.short_description = _('Mark failed logs as "ignored"')

    def retry_failed_logs_action(self, request, queryset):
        """Try to re-apply FAILED trigger log actions in the queryset."""
        count = 0
        for trigger_log in queryset:
            retried = _retry_failed_log(trigger_log)
            if retried:
                count += 1
        self.message_user(
            request,
            _('{count} failed trigger logs retried.').format(count=count),
        )
    retry_failed_logs_action.short_description = _('Retry failed log actions')


admin.site.register([TriggerLog, TriggerLogArchive], TriggerLogAdmin)
