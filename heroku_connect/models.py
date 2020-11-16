from django.conf import settings
from django.core import checks
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from psycopg2 import sql

from heroku_connect.utils import (
    WriteAlgorithm, get_connected_model_for_table_name,
    get_unique_connection_write_mode, hstore_text_to_dict
)


class TriggerLogQuerySet(models.QuerySet):
    """A QuerySet for trigger log models."""

    def failed(self):
        """Filter for log records with sync failures."""
        return self.filter(state=TRIGGER_LOG_STATE['FAILED'])

    def related_to(self, instance):
        """Filter for all log objects of the same connected model as the given instance."""
        return self.filter(table_name=instance.table_name, record_id=instance.record_id)


TRIGGER_LOG_ACTION = {
    'INSERT': 'INSERT',
    'UPDATE': 'UPDATE',
    'DELETE': 'DELETE',
}
"""The type of change that a trigger log object represents."""


TRIGGER_LOG_ACTION_CHOICES = sorted((value, value) for value in TRIGGER_LOG_ACTION.values())


TRIGGER_LOG_STATE = {
    'SUCCESS': 'SUCCESS',
    'MERGED': 'MERGED',
    'IGNORED': 'IGNORED',
    'FAILED': 'FAILED',
    'READONLY': 'READONLY',
    'NEW': 'NEW',
    'IGNORE': 'IGNORE',
    'PENDING': 'PENDING',
    'REQUEUE': 'REQUEUE',
    'REQUEUED': 'REQUEUED',
}
"""The sync state of the change tracked by a trigger log entry."""


TRIGGER_LOG_STATE_CHOICES = sorted((value, value) for value in TRIGGER_LOG_STATE.values())


class TriggerLogAbstract(models.Model):
    """
    Support for accessing the Heroku Connect Trigger Log data and related actions.

    Heroku Connect uses a Trigger Log table to track local changes to connected models (that is,
    in the Heroku database. Such changes are recorded as rows in the trigger log and, for
    read-write mappings, eventually written back to Salesforce.

    Old logs are moved to an archive table (after being processed), from where they are purged
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

    # I18N / TRANSLATIONS:
    #
    # Field names and choices don't use translations, because they refer to (English) technical
    # terms in Heroku Connect's manual. That connection should be preserved. Trigger Log Models
    # are for technical folks and not intended to be user-facing.

    # read-only fields
    # `id` is a BigAutoField for testing convenience;  in a real environment, id management
    # is up to Heroku Connect.
    id = models.BigAutoField(primary_key=True, editable=False)
    txid = models.BigIntegerField(editable=False, null=True)
    created_at = models.DateTimeField(editable=False, null=True)
    updated_at = models.DateTimeField(editable=False, null=True)
    processed_at = models.DateTimeField(editable=False, null=True)
    table_name = models.CharField(max_length=128, editable=False)
    record_id = models.BigIntegerField(editable=False)
    sf_id = models.CharField(max_length=18, editable=False, null=True, db_column='sfid')
    action = models.CharField(max_length=7, editable=False, choices=TRIGGER_LOG_ACTION_CHOICES)
    state = models.CharField(max_length=8, editable=False, null=False, blank=False,
                             choices=TRIGGER_LOG_STATE_CHOICES)
    sf_message = models.TextField(editable=False, null=True, blank=True)

    values = models.TextField(editable=False, null=True, blank=True)
    old = models.TextField(editable=False, null=True, blank=True)

    objects = TriggerLogQuerySet.as_manager()

    class Meta:
        abstract = True
        managed = False
        get_latest_by = 'created_at'
        ordering = ('id',)

    is_archived = False

    @property
    def values_as_dict(self):
        return hstore_text_to_dict(self.values)

    @classmethod
    def capture_insert_from_model(cls, table_name, record_id, *, exclude_fields=()):
        """
        Create a fresh insert record from the current model state in the database.

        For read-write connected models, this will lead to the attempted creation of a
        corresponding object in Salesforce.

        Args:
            table_name (str): The name of the table backing the connected model (without schema)
            record_id (int): The primary id of the connected model
            exclude_fields (Iterable[str]): The names of fields that will not be included in the
                write record

        Returns:
            A list of the created TriggerLog entries (usually one).

        Raises:
            LookupError: if ``table_name`` does not belong to a connected model

        """
        exclude_cols = ()
        if exclude_fields:
            model_cls = get_connected_model_for_table_name(table_name)
            exclude_cols = cls._fieldnames_to_colnames(model_cls, exclude_fields)

        raw_query = sql.SQL("""
            SELECT {schema}.hc_capture_insert_from_row(
              hstore({schema}.{table_name}.*),
              %(table_name)s,
              ARRAY[{exclude_cols}]::text[]  -- cast to type expected by stored procedure
            ) AS id
            FROM {schema}.{table_name}
            WHERE id = %(record_id)s
        """).format(
            schema=sql.Identifier(settings.HEROKU_CONNECT_SCHEMA),
            table_name=sql.Identifier(table_name),
            exclude_cols=sql.SQL(', ').join(sql.Identifier(col) for col in exclude_cols),
        )
        params = {'record_id': record_id, 'table_name': table_name}
        result_qs = TriggerLog.objects.raw(raw_query, params)
        if not result_qs:
            raise TriggerLog.DoesNotExist("TriggerLog was not created after re-capturing INSERT")

        return list(result_qs)  # don't expose raw query; clients only care about the log entries

    @classmethod
    def capture_update_from_model(cls, table_name, record_id, *,
                                  update_fields=(), update_columns=()):
        """
        Create a fresh update record from the current model state in the database.

        For read-write connected models, this will lead to the attempted update of the values of
        a corresponding object in Salesforce.

        Args:
            table_name (str): The name of the table backing the connected model (without schema)
            record_id (int): The primary id of the connected model
            update_fields (Iterable[str]): If given, the names of fields that will be included in
                the write record. These will be converted into database column names.
            update_columns (Iterable[str]): If given, the names of database column names that will
                be included in the write record.

        Returns:
            A list of the created TriggerLog entries (usually one).

        Raises:
            LookupError: if ``table_name`` does not belong to a connected model

        """
        include_cols = set(update_columns)
        if update_fields:
            model_cls = get_connected_model_for_table_name(table_name)
            include_cols.update(cls._fieldnames_to_colnames(model_cls, update_fields))

        raw_query = sql.SQL("""
            SELECT {schema}.hc_capture_update_from_row(
              hstore({schema}.{table_name}.*),
              %(table_name)s,
              ARRAY[%(include_cols)s]
            ) AS id
            FROM {schema}.{table_name}
            WHERE id = %(record_id)s
        """).format(
            schema=sql.Identifier(settings.HEROKU_CONNECT_SCHEMA),
            table_name=sql.Identifier(table_name),
        )
        params = {
            'record_id': record_id,
            'table_name': table_name,
            'include_cols': list(include_cols)
        }
        result_qs = TriggerLog.objects.raw(raw_query, params)
        if not result_qs:
            raise TriggerLog.DoesNotExist("TriggerLog was not created after re-capturing UPDATE")
        return list(result_qs)  # don't expose raw query; clients only care about the log entries

    def __str__(self):
        created_at = self.created_at
        if created_at:
            created_at = '{:%Y-%m-%d %a %H:%M%z}'.format(created_at)
        return (
            '#{id} {action} {table_name}|{record_id} [{created_at}] [{state}]'
        ).format(id=self.id, action=self.action, table_name=self.table_name,
                 record_id=self.record_id, created_at=created_at, state=self.state)

    def get_model(self):
        """
        Fetch the instance of the connected model referenced by this log record.

        Returns:
            The connected instance, or ``None`` if it does not exists.

        """
        model_cls = get_connected_model_for_table_name(self.table_name)
        return model_cls._default_manager.filter(id=self.record_id).first()

    def related(self, *, exclude_self=False):
        """
        Get a QuerySet for all trigger log objects for the same connected model.

        Args:
            exclude_self (bool): Whether to exclude this log object from the result list
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

    def capture_update(self, *, update_fields=(), update_columns=()):
        """Apply :meth:`.TriggerLogAbstract.capture_insert_from_model` for this log."""
        return self.capture_update_from_model(self.table_name, self.record_id,
                                              update_fields=update_fields,
                                              update_columns=update_columns)

    def _recapture(self):
        if self.action == 'INSERT':
            self.capture_insert()
            return True

        elif self.action == 'UPDATE':
            if self.values:
                update_columns = tuple(self.values_as_dict.keys())
            else:
                update_columns = ()

            self.capture_update(update_columns=update_columns)
            return True

        else:
            return False

    @staticmethod
    def _fieldnames_to_colnames(model_cls, fieldnames):
        """Get the names of columns referenced by the given model fields."""
        get_field = model_cls._meta.get_field
        fields = map(get_field, fieldnames)
        return {f.column for f in fields}


class TriggerLog(TriggerLogAbstract):
    """
    Represents entries in the Heroku Connect trigger log.

    .. seealso:: :class:`TriggerLogAbstract`
    """

    is_archived = False

    class Meta(TriggerLogAbstract.Meta):
        db_table = '{schema}"."_trigger_log'.format(schema=settings.HEROKU_CONNECT_SCHEMA)
        verbose_name = _('Trigger Log')

    @transaction.atomic()
    def redo(self):
        """
        Re-sync the change recorded in this trigger log.

        This MAY create new TriggerLog instances, or save changes to this instance.

        Returns:
            A TriggerLog instance that represents the re-application; possibly ``self``.

        """
        if get_unique_connection_write_mode() == WriteAlgorithm.ORDERED_WRITES:
            if self._recapture():
                self.state = TRIGGER_LOG_STATE['REQUEUED']
                self.save(update_fields=['state'])
                return

        self.state = TRIGGER_LOG_STATE['NEW']
        self.save(update_fields=['state'])


class TriggerLogArchive(TriggerLogAbstract):
    """
    Represents entries in the Heroku Connect trigger log archive.

    .. seealso:: :class:`TriggerLogAbstract`
    """

    is_archived = True

    class Meta(TriggerLogAbstract.Meta):
        db_table = '{schema}"."_trigger_log_archive'.format(schema=settings.HEROKU_CONNECT_SCHEMA)
        verbose_name = _('Trigger Log (archived)')
        verbose_name_plural = _('Trigger Logs (archived)')

    @transaction.atomic
    def redo(self):
        """
        Re-sync the change recorded in this trigger log.

        Creates a ``NEW`` live trigger log from the data in this archived trigger log and sets
        the state of this archived instance to ``REQUEUED``.

        .. seealso:: :meth:`.TriggerLog.redo`

        Returns:
            The :class:`.TriggerLog` instance that was created from the data of this archived log.

        """
        if get_unique_connection_write_mode() == WriteAlgorithm.ORDERED_WRITES:
            if self._recapture():
                self.state = TRIGGER_LOG_STATE['REQUEUED']
                self.save(update_fields=['state'])
                return

        trigger_log = self._to_live_trigger_log(state=TRIGGER_LOG_STATE['NEW'])
        trigger_log.save(force_insert=True)  # make sure we get a fresh row
        self.state = TRIGGER_LOG_STATE['REQUEUED']
        self.save(update_fields=['state'])

    def _to_live_trigger_log(self, **kwargs):
        """
        Make a new, non-archived :class:`.TriggerLog` instance with duplicate data.

        Args:
            **kwargs: Set as attributes of the new instance, overriding what would otherwise be
                copied from ``self``.

        Returns:
            The new (unpersisted) :class:`TriggerLog` instance.

        """
        field_names = (field.name for field in TriggerLogAbstract._meta.get_fields())
        attributes = {name: getattr(self, name) for name in field_names}
        del attributes['id']  # this is a completely new log, it should get its own id on save
        attributes.update(kwargs)
        return TriggerLog(**attributes)
