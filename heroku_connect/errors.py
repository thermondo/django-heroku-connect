from itertools import chain

from django.db import transaction

from .models import (
    ErrorTrack, TriggerLog, TriggerLogAbstract, TriggerLogArchive
)


class HerokuModelSyncError(Exception):
    """Represents a failure to sync a connected model back to Salesforce."""

    # It's an exception with the idea that it can be raised, then captured and displayed
    # neatly by Sentry. It might make more sense to turn it into a model with one-to-many
    # related ErrorTracks (see below).

    @classmethod
    def iter(cls):
        """Generate sync errors instances from failed records in the trigger log."""
        for trigger_log in chain(TriggerLog.objects.failed(), TriggerLogArchive.objects.failed()):
            yield HerokuModelSyncError(trigger_log)

    def __new__(cls, trigger_log):
        if FixableHerokuModelSyncError.may_fix(trigger_log):
            return super().__new__(FixableHerokuModelSyncError, trigger_log)
        return super().__new__(HerokuModelSyncError, trigger_log)

    def __init__(self, trigger_log):
        msg = '{log.action} {log.table_name}:{log.record_id} {log.state}'.format(log=trigger_log)
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
        except KeyError:  # pragma: no cover
            raise ValueError("Can't fix {self}".format(self=self))
        with transaction.atomic():
            # prevent collisions with concurrent fixes:
            trigger_log = (
                type(trigger_log)._default_manager  # NoQA
                .select_for_update()
                .get(id=trigger_log.id)
            )
            _, created = ErrorTrack.objects.get_or_create_for_log(trigger_log, is_initial=True)
            if not created:  # pragma: no cover
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
            include = {
                f.name for f in fields
                if not (f.name in exclude or (hasattr(f, 'attname') and f.attname in exclude))
            }
            if include:
                # Attention: passing empty include_fields will update everything
                results.extend(
                    trigger_log.capture_update(update_fields=include)
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
