"""
Django integration for Salesforce using Heroku Connect.

Model classes inheriting from :class:`HerokuConnectModel<heroku_connect.models.HerokuConnectModel>`
can easily be registered with `Heroku Connect`_, which then keeps their tables
in the Heroku database in sync with Salesforce.

.. _`Heroku Connect`: https://devcenter.heroku.com/categories/heroku-connect
"""

default_app_config = 'heroku_connect.apps.HerokuConnectAppConfig'
