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

.. note:: The trigger log models use :class:`django.contrib.postgres.fields.HStoreField` and need
    your ``INSTALLED_APPS`` to include ``'django.contrib.postgres'``.

.. seealso:: :class:`.TriggerLogAbstract` for how to use trigger log models.

.. _Trigger Log:
  https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#understanding-the-trigger-log

.. _fix sync errors:
  https://devcenter.heroku.com/articles/writing-data-to-salesforce-with-heroku-connect#write-errors

Models
^^^^^^

.. automodule:: heroku_connect.models
    :members:
