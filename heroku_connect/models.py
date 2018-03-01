from django.conf import settings
from django.db import models
from django.db.models import F, OuterRef, Subquery
from django.db.models.functions import Coalesce

from heroku_connect.db import models as hc_models


class TriggerLogQuerySet(models.QuerySet):
    """A QuerySet for trigger log models."""

    def failed(self):
        """Filter for log records with sync failures."""
        return self.filter(state=TriggerLogState.FAILED)

    def related_to(self, instance):
        """Filter for all log objects of the same connected model as the given instance."""
        return self.filter(table_name=instance.table_name, record_id=instance.record_id)


class TriggerLogAction:
    """Type of change that a trigger log object represents."""

    INSERT = 'INSERT'
    """A new connected model instance was created locally."""
    UPDATE = 'UPDATE'
    """A connected model instance was updated locally."""
    DELETE = 'DELETE'
    """A connected model instance was deleted locally."""

    @classmethod
    def choices(cls):
        return tuple((getattr(cls, name), name) for name in dir(cls) if name.isupper())


class TriggerLogState:
    """Sync state of the change tracked by a trigger log entry."""

    SUCCESS = 'SUCCESS'
    """Synced to Salesforce."""
    MERGED = 'MERGED'
    """Merged with another local change to be processed together."""
    IGNORED = 'IGNORED'
    """No sync attempted. (Usually because it's not needed.)"""
    FAILED = 'FAILED'
    """Sync attempt failed. Check `sf_message`."""
    READONLY = 'READONLY'
    """Captured update on read-only table."""
    NEW = 'NEW'
    """Newly captured change reedy for processing."""
    IGNORE = 'IGNORE'
    """Newly captured change that needs no syncing."""
    PENDING = 'PENDING'
    """Currently being processed."""

    REQUEUE = 'REQUEUE'
    """Marks a archived entry to be copied back as NEW into the current log."""
    REQUEUED = 'REQUEUED'
    """An archived entry that was copied back into as NEW into the current log."""

    @classmethod
    def choices(cls):
        return tuple((getattr(cls, name), name) for name in dir(cls) if name.isupper())


class TriggerLogAbstract(models.Model):
    """Support for accessing the Heroku Connect Trigger Log data and related actions.

    Heroku Connect uses a Trigger Log table to track local changes to connected models (that is,
    in the Heroku database. Such changes are recorded as rows in the trigger log and, for
    read-write mappings, eventually written back to Salesforce.

    Old logs are moved to an archive table (usually after 24 hours), from where they are purged
    eventually (currently 30 days for paid plans, 7 days for demo). Recent logs are modeled by
    :class:`TriggerLog`; archived logs by :class:`TriggerLogArchive`.

    The data represented by these models is maintained entirely by Heroku Connect, and is
    instrumental to its operations; it should therefore not be modified. A possible exception is
    the ``state`` field, which may be changed as detailed in the `error handling`_ section in the
    Heroku Connect documentation.

    .. seealso::
        - :class:`.TriggerLogQuerySet`
        - `Trigger Log in Heroku Connect docs`_

    .. _Trigger Log in Heroku Connect docs:
        https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#understanding-the-trigger-log
    .. _error handling:
        https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#write-errors

    """

    # read-only fields
    id = models.BigIntegerField(primary_key=True, editable=False)
    created_at = models.DateTimeField(editable=False, null=True)
    updated_at = models.DateTimeField(editable=False, null=True)
    processed_at = models.DateTimeField(editable=False, null=True)
    table_name = models.CharField(max_length=128, editable=False)
    record_id = models.BigIntegerField(editable=False)
    sf_id = models.CharField(max_length=18, editable=False, null=True, db_column='sfid')
    action = models.CharField(max_length=7, editable=False, choices=TriggerLogAction.choices())
    sf_message = models.TextField(editable=False, null=True, blank=True)

    # TODO: these are more useful as HStoreFields (if 'django.contrib.postgres' in INSTALLED_APPS)
    # leave them as textfields for now
    _values = models.TextField(editable=False, null=True, blank=True, db_column='values')
    _old = models.TextField(editable=False, null=True, blank=True, db_column='old')

    # editable fields
    state = models.CharField(max_length=8, null=False, blank=False,
                             choices=TriggerLogState.choices())

    objects = models.Manager.from_queryset(TriggerLogQuerySet)()

    class Meta:
        abstract = True
        managed = False
        get_latest_by = 'created_at'
        ordering = ('id',)

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
        created_at = self.created_at
        if created_at:
            created_at = '{:%Y-%m-%d %a %H:%M%z}'.format(created_at)
        return (
            '#{id} {action} {table_name}|{record_id} [{created_at}] [{state}]'
        ).format(id=self.id, action=self.action, table_name=self.table_name,
                 record_id=self.record_id, created_at=created_at, state=self.state)

    def get_model(self):
        """Fetch the instance of the connected model referenced by this log record.

        Returns:
            The connected instance, or ``None`` if it does not exists.

        """
        model_cls = hc_models.registry.get_class_for_table_name(self.table_name)
        return model_cls._default_manager.filter(id=self.record_id).first()

    def related(self, *, exclude_self=False):
        """Get a QuerySet for all trigger log objects for the same connected model.

        Args:
            exclude_self: Whether to exclude this log object from the result list
        """
        manager = type(self)._default_manager
        queryset = manager.related_to(self)
        if exclude_self:
            queryset = queryset.exclude(id=self.id)
        return queryset

    def capture_insert(self, *, exclude_fields=()):
        """Apply :meth:`.TriggerLogAbstract.capture_insert_from_model` for this log."""
        return self.capture_insert_from_model(self.table_name, self.record_id,
                                              exclude_fields=exclude_fields)

    def capture_update(self, *, update_fields=()):
        """Apply :meth:`.TriggerLogAbstract.capture_insert_from_model` for this log."""
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

    .. seealso:: :class:`TriggerLogAbstract`
    """

    is_archived = False

    class Meta(TriggerLogAbstract.Meta):
        db_table = '{schema}"."_trigger_log'.format(schema=settings.HEROKU_CONNECT_SCHEMA)
        verbose_name = 'Current Trigger Log'


class TriggerLogArchive(TriggerLogAbstract):
    """Represents entries in the Heroku Connect trigger log archive.

    .. seealso:: :class:`TriggerLogAbstract`
    """

    is_archived = True

    class Meta(TriggerLogAbstract.Meta):
        db_table = '{schema}"."_trigger_log_archive'.format(schema=settings.HEROKU_CONNECT_SCHEMA)
        verbose_name = 'Archived Trigger Log'


class TriggerLogPermanent(TriggerLogAbstract):
    """Keep a permanent copy of trigger log data in a table managed by us, not Heroku Connect.

    .. seealso:: :class:`TriggerLogAbstract`
    """

    class Meta(TriggerLogAbstract.Meta):
        abstract = False
        managed = True
        verbose_name = 'Permanent Trigger Log'
        index_together = (
            ('table_name', 'record_id', 'id'),  # for lookup of related trigger logs
        )

    @classmethod
    def create_unknown(cls, logs):
        """Copy any TriggerLog instance to TriggerLogPermanent, unless it exists already.

        Raises:
            IntegrityError: if called concurrently for the same TriggerLog instances

        """
        field_names = [f.name for f in TriggerLogAbstract._meta.get_fields()]
        existing_ids = set(cls.objects.values_list('id', flat=True))
        to_create = [log for log in logs if log.id not in existing_ids]
        TriggerLogPermanent.objects.bulk_create(
            TriggerLogPermanent(**{name: getattr(log, name) for name in field_names})
            for log in to_create
        )

    def related_surrounding(self):
        """Get a QuerySet for related trigger logs, up to the previous and next successful ones."""
        related_logs = TriggerLogPermanent.objects.filter(
            table_name=OuterRef('table_name'),
            record_id=OuterRef('record_id'),
        )
        log_id = self.id
        return (
            self
            .related()
            .annotate(
                previous_success_id=Coalesce(
                    Subquery(
                        related_logs
                        .filter(
                            state=TriggerLogState.SUCCESS,
                            id__lt=log_id,
                        )
                        .order_by('-id')  # latest first
                        .values('id')[:1]
                    ),
                    -9223372036854775808,  # min bigint
                    # https://www.postgresql.org/docs/9.6/static/datatype-numeric.html
                ),
                next_success_id=Coalesce(
                    Subquery(
                        related_logs
                        .filter(
                            state=TriggerLogState.SUCCESS,
                            id__gt=log_id,
                        )
                        .order_by('id')  # earliest first
                        .values('id')[:1]
                    ),
                    9223372036854775807,  # max bigint
                    # https://www.postgresql.org/docs/9.6/static/datatype-numeric.html
                ),
            )
            .filter(id__gte=F('previous_success_id'), id__lte=F('next_success_id'))
        )
