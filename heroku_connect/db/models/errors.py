from django.db import models, transaction

from .triggerlog import (
    TriggerLog, TriggerLogAbstract, TriggerLogArchive
)


class HerokuModelSyncError(Exception):
    """Represents a failure to sync a connected model back to Salesforce"""

    # It's an exception with the idea that it can be raised, then captured and displayed
    # neatly by Sentry. It might make more sense to turn it into a model with one-to-many
    # related ErrorTracks (see below).

    @classmethod
    def iter(cls):
        """Generate sync errors instances from failed records in the trigger log"""
        for trigger_log in TriggerLog.objects.failed().combined():
            yield HerokuModelSyncError(trigger_log)

    def __new__(cls, trigger_log):
        if FixableHerokuModelSyncError.may_fix(trigger_log):
            return super().__new__(FixableHerokuModelSyncError, trigger_log)
        return super().__new__(HerokuModelSyncError, trigger_log)

    def __init__(self, trigger_log):
        msg = '{log.action} {log.table_name} {log.record_id}'.format(log=trigger_log)
        super().__init__(msg)
        self.trigger_log = trigger_log
        self.model = trigger_log.get_model()


class FixableHerokuModelSyncError(HerokuModelSyncError):
    """Error which exposes methods to attempt a fix.

    The general fixing method follows the recommendations for `Write Errors`_ in the Heroku Connect
    doc for their `Ordered Writes Algorithm`_. Basically, it can fix inserts and updates by
    creating a new trigger log record from the current state of the connected model, while allowing
    to exclude or delay certain fields.

    .. _Write Errors:
        https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#write-errors
    .. _Ordered Writes Algorithm:
        https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#ordered-writes-algorithm

    """
    FIXABLE_ACTIONS = {TriggerLog.Action.INSERT, TriggerLog.Action.UPDATE}
    FIXABLE_STATES = {TriggerLog.State.FAILED}

    @classmethod
    def may_fix(cls, trigger_log):
        return (
            trigger_log.action in cls.FIXABLE_ACTIONS and
            trigger_log.state in cls.FIXABLE_STATES and
            not ErrorTrack.objects.of_log(trigger_log).exists()
        )

    def fix(self, *, delay_fields=(), update_model=None):
        """Try to fix the error, possibly by making changes to the model.

        Acquires a database lock on the associated trigger_log entry.

        Args:
            delay_fields: An iterable of fieldnames that will be excluded from the first step
                of the fix.
            update_model: A dict of ``{field_name: value}`` that will be set on the model.
        """
        delay_fields = set(delay_fields)
        update_model = dict(update_model) if update_model else {}
        trigger_log = self.trigger_log
        try:
            fixer = {
                TriggerLogAbstract.Action.INSERT: self._fix_insert,
                TriggerLogAbstract.Action.UPDATE: self._fix_update,
            }[trigger_log.action]
        except KeyError:
            raise ValueError("Can't fix {self}".format(self=self))
        with transaction.atomic():
            # prevent collisions with concurrent fixes:
            trigger_log = (
                type(trigger_log)._default_manager  # NoQA
                .select_for_update()
                .get(id=trigger_log.id)
            )
            _, created = ErrorTrack.objects.get_or_create_for_log(trigger_log, is_initial=True)
            if not created:
                # somebody created an ErrorTrack concurrently
                return
            results = fixer(trigger_log, delay_fields=delay_fields, update_model=update_model)
            for log in results:
                ErrorTrack.objects.get_or_create_for_log(log, is_initial=False)

    @classmethod
    def _fix_insert(cls, trigger_log, *, delay_fields, update_model):
        results = []
        exclude = set(delay_fields) | update_model.keys()
        results.extend(
            trigger_log.capture_insert(exclude_fields=exclude)
        )
        if delay_fields or update_model:
            results.extend(
                cls._fix_update(trigger_log, delay_fields=(), update_model=update_model)
            )
        return results

    @classmethod
    def _fix_update(cls, trigger_log, *, delay_fields, update_model):
        results = []
        exclude = set(delay_fields) | update_model.keys()
        if exclude:
            model = trigger_log.get_model()
            fields = type(model)._meta.get_fields()
            include = {f.name for f in fields if not {f.name, f.attname}.issubset(exclude)}
            if include:
                # Attention: passing empty include_fields will update everything
                results.extend(
                    trigger_log.capture_update(include_fields=include)
                )
            if update_model:
                cls._update_model(model, update_model)
        else:
            results.extend(
                trigger_log.capture_update()
            )
        return results

    @classmethod
    def _update_model(cls, model, mapping):
        for name, value in mapping.items():
            setattr(model, name, value)
        model.save(update_fields=mapping.keys())  # this will generate a new trigger_log entry


class ErrorTrackQuerySet(models.QuerySet):

    def of_log(self, log):
        # Abstract away the details of how log record and it's track are connected
        return self.filter(trigger_log_id=log.id)

    def orphaned(self):
        """Filter for ErrorTracks whose related TriggerLogs do not exist anymore"""
        return (
            self
            .exclude(trigger_log_id__in=TriggerLog.objects.values_list('id'))
            .exclude(trigger_log_id__in=TriggerLogArchive.objects.values_list('id'))
            # interestingly, excludes seem to perform faster than a query with Exists(...)
        )


class ErrorTrackManager(models.Manager.from_queryset(ErrorTrackQuerySet)):

    def get_or_create_for_log(self, trigger_log, **defaults):
        _defaults = {
            name: getattr(trigger_log, name)
            for name in {'created_at', 'table_name', 'record_id', 'action', 'state', 'sf_message'}
        }
        _defaults.update(defaults)
        return self.get_or_create(trigger_log_id=trigger_log.id, defaults=_defaults)


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
        """The track's related trigger log entry if it exists, or None."""
        try:
            log = self._log
        except AttributeError:
            log = self._log = (
                TriggerLog.objects.filter(id=self.trigger_log_id).first() or
                TriggerLogArchive.filter(id=self.trigger_log_id).first()
            )
        return log
