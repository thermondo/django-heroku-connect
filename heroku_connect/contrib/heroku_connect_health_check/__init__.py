"""
Health Check for Heroku Connect.

Simply add the following to your ``INSTALLED_APPS`` setting::

    INSTALLED_APPS = [
        # ...
        'heroku_connect.contrib.heroku_connect_health_check',
        # ...
    ]

Note:

    This features requires `django-health-check`_ to be installed.

.. _`django-health-check`: https://github.com/KristianOellegaard/django-health-check
"""
default_app_config = 'heroku_connect.contrib.heroku_connect_health_check.apps.HealthCheckConfig'
