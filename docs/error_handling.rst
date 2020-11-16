Error handling
==============

Trigger Log
-----------

Heroku Connect uses the `Trigger Log`_ to track changes to connected model
instances, as well as its own efforts to sync them to Salesforce.

*django-heroku-connect* exposes the trigger log tables, which are managed by
Heroku Connect, as Django models :class:`.TriggerLog` and
:class:`.TriggerLogArchive`. These models also offer access to database stored
procedures provided by Heroku Connect to `fix sync errors`_.

.. seealso:: :class:`.TriggerLogAbstract` for how to use trigger log models.

.. _Trigger Log:
  https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#understanding-the-trigger-log

.. _fix sync errors:
  https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#write-errors


Admin actions
^^^^^^^^^^^^^

The admins for the trigger log models (discussed below) offer actions to *ignore* or *retry* failed
trigger log entries. The former simply sets the state of the entry to ``IGNORED``, if you want to
clean up for whatever reason.

*Retrying* means an attempt to re-sync the change represented by the trigger log. This entails
creating an identical trigger log row in ``NEW`` state, either by simply changing the failed
row's state (:class:`.TriggerLog`), or by copying an archived row back into
the live TriggerLog and setting the archived state to ``REQUEUED``
(:class:`.TriggerLogArchive`). Heroku Connect will then normally process that
row.

If this simple attempt at a fix does not work, try to manually call
:meth:`capture_insert() <.TriggerLogAbstract.capture_insert>` or
:meth:`capture_update() <.TriggerLogAbstract.capture_update>` on a failed trigger log instance.


Models
^^^^^^

.. automodule:: heroku_connect.models
    :members:
