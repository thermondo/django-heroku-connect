from collections import OrderedDict
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from heroku_connect.models import ErrorTrack, TriggerLog, TriggerLogArchive


def _replaced(__values, **__replacements):
    """Replace values with replacements from an alias dict, suppressing empty replacements."""
    return tuple(o for o in (__replacements.get(name, name) for name in __values) if o)


def _build_admin_filter_url(model, obj, *, fields):
    """Build a filter URL to an admin changelist based on an object's field values."""
    if not all(getattr(obj, name, None) for name in fields):
        return None
    filter_query = {name: getattr(obj, name) for name in fields}
    content_type = ContentType.objects.get_for_model(model)
    url = reverse('admin:{app_label}_{model}_changelist'.format(**content_type.__dict__))
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    query.update(filter_query)
    parts_with_filter = parts._replace(query=urlencode(query))
    return urlunsplit(parts_with_filter)


def _make_filter_link(primary_field, *fields, name=None):
    """Create a function that links to a list of all objects with the same field values."""
    fields = (primary_field,) + fields
    url_template = '<a href="{url}">{name_or_value}</a>'
    no_url_template = '<span style="color: pink;">{value}</span>'

    def field_link(self, obj):
        model = type(obj)
        value = getattr(obj, primary_field, None)
        name_or_value = name or value
        if all(getattr(obj, field, None) for field in fields):
            url = _build_admin_filter_url(model, obj, fields=fields)
            if url:
                return format_html(url_template, **locals())
        return format_html(no_url_template, **locals())
    field_link.allow_tags = True
    field_link.short_description = primary_field.replace('_', ' ').capitalize()
    field_link.admin_order_field = primary_field
    field_link.__name__ = field_link.__name__.replace('field', primary_field)

    return field_link


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
        ('created_at', 'action', 'table_name', 'record_id', 'sf_message', 'state',),
        **field_overrides)
    list_filter = ('action', 'state', 'table_name')
    list_per_page = 100
    list_max_show_all = 200
    search_fields = ('record_id', 'sf_id', 'sf_message')

    # DETAIL
    readonly_fields = _replaced(
        [field.name for field in TriggerLog._meta.get_fields() if not field.editable],
        **field_overrides)
    save_as = True
    save_on_top = True

    table_name_link = _make_filter_link('table_name')
    record_id_link = _make_filter_link('record_id', 'table_name')

    def action_label(self, log):
        action = log.action
        return format_html('<span class="label label-default">{action}</span>', action=action)
    action_label.allow_tags = True
    action_label.short_description = 'Action'
    action_label.admin_order_field = 'action'

    def state_label(self, log):
        state = log.state
        mod = {
            TriggerLog.State.SUCCESS: 'success',
            TriggerLog.State.FAILED: 'danger label-important',  # fallback for bootstrap 2
            TriggerLog.State.NEW: 'primary label-inverse',  # fallback for bootstrap 2
            TriggerLog.State.PENDING: 'info',
            TriggerLog.State.REQUEUE: 'warning',
            TriggerLog.State.REQUEUED: 'warning',
        }.get(state, 'default')
        return format_html('<span class="label label-{mod}">{state}</a>', mod=mod, state=state)
    state_label.allow_tags = True
    state_label.short_description = 'State'
    state_label.admin_order_field = 'state'


@admin.register(TriggerLog)
class TriggerLogAdmin(GenericLogModelAdmin):
    actions = ['create_error_tracks']
    actions_on_top = True

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return OrderedDict(
            (name, value) for name, value in super().get_actions(request).items()
            if name != 'delete_selected'
        )

    @staticmethod
    def create_error_tracks(modeladmin, request, queryset):
        """Create ErrorTracks for the queryset if they don't exist yet.

        If a track for the first log in the queryset (lowest id) does not exist yet, it is created
        with ``is_initial=True``; the others get created with a default value of ``False``.
        """
        error_tracks = ErrorTrack._meta.verbose_name_plural
        model_plural = queryset.model._meta.verbose_name_plural
        selected_count = queryset.count()
        created_count = existed_count = 0

        for track, created in ErrorTrack.objects.get_or_create_for_multiple(queryset):
            if created:
                created_count += 1
            else:
                existed_count += 1
        if existed_count:
            msg = _('Created {created_count} {error_tracks} ({existed_count} already existed)'
                    ' for {selected_count} {model_plural}')
        else:
            msg = _('Created {created_count} {error_tracks} for {selected_count} {model_plural}')
        modeladmin.message_user(request, msg.format(**locals()), level=messages.SUCCESS)
    create_error_tracks.short_description = (
        _('Create {error_tracks} for selected objects')
        .format(error_tracks=ErrorTrack._meta.verbose_name_plural)
    )


admin.register(TriggerLogArchive)(TriggerLogAdmin)


@admin.register(ErrorTrack)
class ErrorTrackAdmin(GenericLogModelAdmin):

    # LIST
    list_display = (
            GenericLogModelAdmin.list_display +
            ('trigger_log_link', 'is_initial',))
    list_filter = GenericLogModelAdmin.list_filter + ('is_initial',)

    # DETAIL
    readonly_fields = _replaced(
        (field.name for field in ErrorTrack._meta.get_fields() if not field.editable),
        **GenericLogModelAdmin.field_overrides)

    def trigger_log_link(self, track):
        log = track.log
        url = None
        log_id = (log and log.id) or track.trigger_log_id
        if log:
            try:
                content_type = ContentType.objects.get_for_model(type(log))
                url = reverse(
                    'admin:{app_label}_{model}_change'.format(**content_type.__dict__),
                    args=(log.id,),
                )
            except (ContentType.DoesNotExist, NoReverseMatch) as error:
                pass
        if url:
            return format_html('<a href="{url}">{log_id}</a>', log_id=log_id, url=url)
        return format_html('{log_id}', log_id=log_id)
    trigger_log_link.allow_tags = True
    trigger_log_link.short_description = 'Trigger log id'
    trigger_log_link.admin_order_field = 'trigger_log_id'
