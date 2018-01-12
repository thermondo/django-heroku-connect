|version| |ci| |coverage| |license|

Django Heroku Connect
=====================

**Django integration Salesforce using Heroku Connect.**

Quick Start
-----------

We have a `Deploy to Heroku sample`_ that gets you started in less than a
minute.

.. _`Deploy to Heroku sample`: https://github.com/Thermondo/django-heroku-connect-sample

Documentation
-------------

Check out the full documentation at here:
https://django-heroku-connect.readthedocs.io/

Install
-------

Simply install the PyPi package…

.. code:: shell

    pip install django-heroku-connect

…and add ``heroku_connect`` to the ``INSTALLED_APP`` settings.

Last but not least make sure change the database engine, e.g.:

.. code:: python

    import dj_database_url

    DATABASES['default'] = dj_database_url.config(
        engine='heroku_connect.db.backends.postgres'
    )

    # or for PostGIS support:

    DATABASES['default'] = dj_database_url.config(
        engine='heroku_connect.db.backends.postgis'
    )


.. |version| image:: https://img.shields.io/pypi/v/django-heroku-connect.svg
   :target: https://pypi.python.org/pypi/django-heroku-connect/
.. |ci| image:: https://api.travis-ci.org/Thermondo/django-heroku-connect.svg?branch=master
   :target: https://travis-ci.org/Thermondo/django-heroku-connect
.. |coverage| image:: https://codecov.io/gh/Thermondo/django-heroku-connect/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/Thermondo/django-heroku-connect
.. |license| image:: https://img.shields.io/badge/license-Apache_2-blue.svg
   :target: LICENSE
