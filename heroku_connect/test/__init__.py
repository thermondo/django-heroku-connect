"""
Extensions for Django's test framework to add support for Heroku Connect.

The custom database engine will create the Heroku Connect schema for you.
The schema is created right via the
:data:`pre_migrate<django.db.models.signals.pre_migrate>` signal, only when a
test database is created. This will work for both Django's build in test
suite as well as `pytest-django`_ and maybe others.

.. _`pytest-django`: https://github.com/pytest-dev/pytest-django
"""
