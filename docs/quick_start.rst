Quick Start
===========

Deploy to Heroku
----------------

We have a `Deploy to Heroku sample`_ that gets you started in less than a
minute.

.. _`Deploy to Heroku sample`: https://github.com/Thermondo/django-heroku-connect-sample

Setup
-----

Simply install the PyPi package…

.. code:: shell

    pip install django-heroku-connect

…and add ``heroku_connect`` to the ``INSTALLED_APP`` settings.

Last but not least make sure to change the database engine, e.g.:

.. code:: python

    import dj_database_url

    DATABASES['default'] = dj_database_url.config(
        engine='heroku_connect.db.backends.postgres'
    )

    # or for PostGIS support:

    DATABASES['default'] = dj_database_url.config(
        engine='heroku_connect.db.backends.postgis'
    )

Example
-------

This is what your ``models.py`` might look like:

.. code:: python

    from django.db import models
    from heroku_connect.db import models as hc_models


    class User(hc_models.HerokuConnectModel):
        sf_object_name = 'User'

        username = hc_models.Text(
            sf_field_name='Username', max_length=80)
        email = hc_models.Email(sf_field_name='Email')
        department = hc_models.Text(
            sf_field_name='Department', max_length=80)
        title = hc_models.Text(sf_field_name='Title', max_length=80)


    class UserComment(models.Model):
        user = models.ForeignKey(User, to_field='sf_id',
                                 on_delete=models.SET_NULL, null=True)
        comment = models.TextField()

In this example we read-only synchronize the ``User`` object to your Django
application. We add another model, ``UserComment`` which is managed by
Django you can write to it and set a foreign relation to the User object.
Note that you should never use the internal primary key for foreign
relations. This key may change when Heroku Connect re-synchronizes your
table.

Deployment
----------

.. note:: For convenience you will need the `Heroku Connect CLI Plugin`_.

Make sure to set your `Salesforce Organization ID`_ in your Heroku
application environment.

.. code:: shell

    heroku config:set HEROKU_CONNECT_ORGANIZATION_ID=00Dxxx
    # You want to add it to your local environment too,
    # to execute some management commands locally.
    export HEROKU_CONNECT_ORGANIZATION_ID=00Dxxx


Next deploy your code to Heroku, using your preferred method.

As a next step you will need to provision and setup the Heroku Connect
add-on if you haven't already. Simply follow the `Heroku Connect tutorial`_.

As a final step, import the correct mappings:

.. code:: shell

    python manage.py makemappings -o hc_mappings.json
    heroku connect:import hc_mappings.json

That's it, enjoy!

.. _`Heroku Connect CLI Plugin`:
    https://github.com/heroku/heroku-connect-plugin
.. _`Salesforce Organization ID`:
    https://help.salesforce.com/articleView?id=000006019
.. _`Heroku Connect tutorial`:
    https://github.com/heroku/heroku-connect-plugin#tutorial
