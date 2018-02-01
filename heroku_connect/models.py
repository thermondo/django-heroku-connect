from operator import itemgetter

from django.conf import settings
from django.db import connection, models
from django.db.models import F, OuterRef, Q, Subquery
from django.db.models.signals import pre_migrate
from django.dispatch import receiver

from heroku_connect.db import models as hc_models


class TriggerLogQuerySet(models.QuerySet):

    def failed(self):
        """Filter for log records with sync failures."""
        return self.filter(state=TriggerLog.State.FAILED)

    def related_to(self, instance):
        """Filter for all log objects of the same connected model as the given instance."""
        return self.filter(table_name=instance.table_name, record_id=instance.record_id)

    def initial_failures(self):
        """Filter for trigger logs that started a chain of failures.

        They are the first failed logs which are not preceded by another failure without at least
        one success in between.
        """
        ordered = self.order_by('id')  # TODO replace self.order_by to prevent subsequent changes
        return (
            ordered
            .failed()
            .annotate(
                previous_failure_id=Subquery(
                    TriggerLog.objects.filter(
                        state='FAILED',
                        table_name=OuterRef('table_name'),
                        record_id=OuterRef('record_id'),
                        id__lt=OuterRef('id')
                    ).values('id')[:1]
                ),
                previous_archived_failure_id=Subquery(
                    TriggerLogArchive.objects.filter(
                        state='FAILED',
                        table_name=OuterRef('table_name'),
                        record_id=OuterRef('record_id'),
                        id__lt=OuterRef('id')
                    ).values('id')[:1]
                ),
                previous_success_id=Subquery(
                    TriggerLog.objects.filter(
                        state='SUCCESS',
                        table_name=OuterRef('table_name'),
                        record_id=OuterRef('record_id'),
                        id__lt=OuterRef('id')
                    ).values('id')[:1]
                ),
                previous_archived_success_id=Subquery(
                    TriggerLog.objects.filter(
                        state='SUCCESS',
                        table_name=OuterRef('table_name'),
                        record_id=OuterRef('record_id'),
                        id__lt=OuterRef('id')
                    ).values('id')[:1]
                ),
            )
            .filter(
                Q(
                    previous_failure_id__isnull=True,
                    previous_archived_failure_id__isnull=True
                ) |
                Q(previous_success_id__gt=F('previous_failure_id')) |
                Q(previous_success_id__gt=F('previous_archived_failure_id')) |
                Q(previous_archived_success_id__gt=F('previous_failure_id')) |
                Q(previous_archived_success_id__gt=F('previous_archived_failure_id'))
            )
        )


class TriggerLogAbstract(models.Model):
    """Support for accessing the Heroku Connect Trigger Log data and related actions.

    Heroku Connect uses a Trigger Log table to track local changes to connected models (that is,
    in the Heroku database. Such changes are recorded as rows in the trigger log and, for
    read-write mappings, eventually written back to Salesforce.

    Old logs are moved to an archive table (usually after 24 hours), from where they are purged
    eventually (currently 30 days for paid plans, 7 days for demo). Recent logs are modeled by
    :cls:`TriggerLog`; archived logs by :cls:`TriggerLogArchive`.

    The data represented by these models is maintained entirely by Heroku Connect, and is
    instrumental to its operations; it should therefore not be modified. A possible exception is
    the ``state`` field, which may be changed as detailed in the `error handling`_ section in the
    Heroku Connect documentation.

    .. seealso::
        `Heroku Connect doc`_
            Details about the Trigger Log.

    .. _Heroku Connect doc:
        https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#understanding-the-trigger-log
    .. _error handling:
        https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#write-errors

    """

    class Action:
        """Type of change that a trigger log object represents."""

        INSERT = 'INSERT'
        UPDATE = 'UPDATE'
        DELETE = 'DELETE'

        @classmethod
        def choices(cls):
            return tuple((getattr(cls, name), name) for name in dir(cls) if name.isupper())

        @classmethod
        def values(cls):
            return map(itemgetter(0), cls.choices())

    class State:
        """Sync state of the change."""

        SUCCESS = 'SUCCESS'
        MERGED = 'MERGED'
        IGNORED = 'IGNORED'
        FAILED = 'FAILED'
        READONLY = 'READONLY'
        NEW = 'NEW'
        IGNORE = 'IGNORE'
        PENDING = 'PENDING'

        REQUEUE = 'REQUEUE'
        REQUEUED = 'REQUEUED'

        @classmethod
        def choices(cls):
            return tuple((getattr(cls, name), name) for name in dir(cls) if name.isupper())

        @classmethod
        def values(cls):
            return map(itemgetter(0), cls.choices())

    # read-only fields
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    updated_at = models.DateTimeField(editable=False, null=True)
    processed_at = models.DateTimeField(editable=False, null=True)
    table_name = models.CharField(max_length=128, editable=False)
    record_id = models.BigIntegerField(editable=False)
    sf_id = models.CharField(max_length=18, editable=False, null=True, db_column='sfid')
    action = models.CharField(max_length=7, editable=False, choices=Action.choices())
    sf_message = models.TextField(editable=False, null=True, blank=True)

    # TODO: these are more useful as HStoreFields (if 'django.contrib.postgres' in INSTALLED_APPS)
    # leave them as textfields for now
    _values = models.TextField(editable=False, db_column='values')
    _old = models.TextField(editable=False, null=True, blank=True, db_column='old')

    # editable fields
    state = models.CharField(max_length=8, null=False, blank=False, choices=State.choices())

    objects = models.Manager.from_queryset(TriggerLogQuerySet)()

    class Meta:
        abstract = True
        managed = False
        get_latest_by = 'created_at'
        ordering = ('-created_at', '-id')

    is_archived = False

    @classmethod
    def capture_insert_from_model(cls, table_name, record_id, *, exclude_fields=()):
        """Create a fresh insert record from the current model state in the database.

        For read-write connected models, this will lead to the attempted creation of a
        corresponding object in Salesforce.

        Args:
            table_name: The name of the table backing the connected model (without schema)
            record_id: The primary id of the connected model
            exclude_fields: The names of fields that will not be included in the write record

        Raises:
            LookupError: if ``table_name`` does not belong to a connected model

        """
        exclude_cols = ()
        if exclude_fields:
            model_cls = hc_models.registry.get_class_for_table_name(table_name)
            exclude_cols = cls._fieldnames_to_colnames(model_cls, exclude_fields)

        sql = """
            SELECT "{schema}".hc_capture_insert_from_row(
              hstore({schema}.{table_name}.*),
              '{table_name}',
              ARRAY[{exclude_cols}]::text[]
            ) AS id
            FROM "{schema}"."{table_name}"
            WHERE id = %(record_id)s
        """.format(
            # TODO escape
            schema=settings.HEROKU_CONNECT_SCHEMA,
            table_name=table_name,
            exclude_cols=', '.join("'{}'".format(col) for col in exclude_cols)
        )
        params = {'record_id': record_id}
        return list(TriggerLog.objects.raw(sql, params))

    @classmethod
    def capture_update_from_model(cls, table_name, record_id, *, update_fields=()):
        """Create a fresh update record from the current model state in the database.

        For read-write connected models, this will lead to the attempted update of the values of
        a corresponding object in Salesforce.

        Args:
            table_name: The name of the table backing the connected model (without schema)
            record_id: The primary id of the connected model
            update_fields: If given, the names of fields that will be included in the write record

        Raises:
            LookupError: if ``table_name`` does not belong to a connected model

        """
        include_cols = ()
        if update_fields:
            model_cls = hc_models.registry.get_class_for_table_name(table_name)
            include_cols = cls._fieldnames_to_colnames(model_cls, update_fields)
        sql = """
            SELECT "{schema}".hc_capture_update_from_row(
              hstore({schema}.{table_name}.*),
              '{table_name}',
              ARRAY[{include_cols}]::text[]
            ) AS id
            FROM "{schema}"."{table_name}"
            WHERE id = %(record_id)s
        """.format(
            # TODO escape
            schema=settings.HEROKU_CONNECT_SCHEMA,
            table_name=table_name,
            include_cols=', '.join("'{}'".format(col) for col in include_cols),
        )
        params = {'record_id': record_id}
        return list(TriggerLog.objects.raw(sql, params))

    def __str__(self):
        return (
            '#{id} {action} {table_name}|{record_id} [{created_at:%Y-%m-%d %a %H:%M%z}] [{state}]'
        ).format(id=self.id, action=self.action, table_name=self.table_name,
                 record_id=self.record_id, created_at=self.created_at, state=self.state)

    def get_model(self):
        """Fetch the instance of the connected model referenced by this log record.

        Returns:
            The connected instance, or ``None`` if it does not exists.

        """
        model_cls = hc_models.registry.get_class_for_table_name(self.table_name)
        return model_cls._default_manager.filter(id=self.record_id).first()

    def related(self, *, exclude_self=False):
        """Get a queryset for all trigger log objects for the same connected model.

        Args:
            exclude_self: Whether to exclude this log object from the result list
        """
        manager = type(self)._default_manager
        queryset = manager.related_to(self)
        if exclude_self:
            queryset = queryset.exclude(id=self.id)
        return queryset

    def capture_insert(self, *, exclude_fields=()):
        """Apply :meth:`TriggerLog.capture_insert_from_model` for this log."""
        return self.capture_insert_from_model(self.table_name, self.record_id,
                                              exclude_fields=exclude_fields)

    def capture_update(self, *, update_fields=()):
        """Apply :meth:`TriggerLog.capture_insert_from_model` for this log."""
        return self.capture_update_from_model(self.table_name, self.record_id,
                                              update_fields=update_fields)

    @staticmethod
    def _fieldnames_to_colnames(model_cls, fieldnames):
        """Get the names of columns referenced by the given model fields."""
        get_field = model_cls._meta.get_field
        fields = map(get_field, fieldnames)
        return {f.column for f in fields}


class TriggerLog(TriggerLogAbstract):
    """Represents entries in the Heroku Connect trigger log.

    .. seealso::
        Class :cls:`TriggerLogAbstract`
            for more details about the trigger log
    """

    is_archived = False

    class Meta(TriggerLogAbstract.Meta):
        db_table = '{schema}"."_trigger_log'.format(schema=settings.HEROKU_CONNECT_SCHEMA)


class TriggerLogArchive(TriggerLogAbstract):
    """Represents entries in the Heroku Connect trigger log archive.

    .. seealso::
        Class :cls:`TriggerLogAbstract`
            for more details about the trigger log
    """

    is_archived = True

    class Meta(TriggerLogAbstract.Meta):
        db_table = '{schema}"."_trigger_log_archive'.format(schema=settings.HEROKU_CONNECT_SCHEMA)


@receiver(pre_migrate)
def set_hstore(sender, app_config, **kwargs):
    command = 'CREATE EXTENSION IF NOT EXISTS HSTORE;'
    with connection.cursor() as cursor:
        cursor.execute(command)


class ErrorTrackQuerySet(models.QuerySet):

    def of_log(self, log):
        # Abstract away the details of how log record and it's track are connected
        return self.filter(trigger_log_id=log.id)

    def orphaned(self):
        """Filter for ErrorTracks whose related TriggerLogs do not exist anymore."""
        return (
            self
            .exclude(trigger_log_id__in=TriggerLog.objects.values_list('id'))
            .exclude(trigger_log_id__in=TriggerLogArchive.objects.values_list('id'))
            # excludes seem to perform faster than a query with Exists(...)
        )


class ErrorTrackManager(models.Manager.from_queryset(ErrorTrackQuerySet)):

    def get_or_create_for_log(self, trigger_log, *, is_initial=None, **defaults):
        if is_initial is None:
            cls_objects = type(trigger_log)._default_manager
            is_initial = cls_objects.initial_failures().filter(id=trigger_log.id).exists()
        _defaults = {
            name: getattr(trigger_log, name)
            for name in {'created_at', 'table_name', 'record_id', 'action', 'state', 'sf_message'}
        }
        _defaults.update(defaults)
        _defaults['is_initial'] = is_initial
        return self.get_or_create(trigger_log_id=trigger_log.id, defaults=_defaults)

    def get_or_create_for_multiple(self, logs):
        for log in logs:
            t, created = self.get_or_create_for_log(log, is_initial=None)
            yield t, created


class ErrorTrack(models.Model):
    """Extra data to associate with entries in the trigger log.

    The idea is to track which trigger log entries are involved in the recognition and
    resolution of errors. It's useful for answering questions like:

    * Has a fix already been tried for a failed log record?
    * Has it succeeded?

    Because trigger log entries are tracked across the live and archive tables, the tracks survive
    the eventual automatic purge of their respective entries, and manual cleanup is needed. On the
    other hand, this can be used to build a longer history of error data than the Trigger Log
    itself allows.
    """

    # The following fields uniquely identify the trigger log entry an ErrorTrack belongs to.
    # A foreign key does not work, unfortunately, because a log entry can move between the
    # actual trigger log and the archive table.
    # Side note: Has anyone ever run out of big serial ids? Then we should use (id, created_at) as
    # composite foreign keys.
    trigger_log_id = models.BigIntegerField(unique=True, editable=False)

    # The following fields are duplicated from TriggerLog, so information can be retained after
    # Heroku Connect purges the trigger log. It also makes queries for these fields easier, since
    # the lack of a true foreign key negates a lot of Django's ORM features.
    created_at = models.DateTimeField(editable=False)
    table_name = models.CharField(max_length=128, editable=False)
    record_id = models.BigIntegerField(editable=False)
    action = models.CharField(max_length=7, editable=False)
    state = models.CharField(max_length=8, null=False, blank=False, editable=False)
    sf_message = models.TextField(editable=False, null=True, blank=True)

    # Additional data:
    is_initial = models.BooleanField()

    objects = ErrorTrackManager()

    def __str__(self):
        return (
            '{action} {table_name}|{record_id} [{created_at:%Y-%m-%d %a %H:%M%z}] {state}'.format(
                action=self.action, table_name=self.table_name, record_id=self.record_id,
                created_at=self.created_at, state=self.state)
        )

    @property
    def log(self):
        """Return the track's related trigger log entry if it exists, or None."""
        try:
            log = self._log
        except AttributeError:
            log = self._log = (
                TriggerLog.objects.filter(id=self.trigger_log_id).first() or
                TriggerLogArchive.objects.filter(id=self.trigger_log_id).first()
            )
        return log

    def refresh_from_db(self, **kwargs):
        try:
            del self._log  # clear cached related trigger log
        except AttributeError:
            pass
        super().refresh_from_db(**kwargs)
