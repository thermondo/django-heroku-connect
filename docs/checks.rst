Checks
======

Model Checks
------------

``heroku_connect.E001``
~~~~~~~~~~~~~~~~~~~~~~~

The class attribute :attr:`HerokuConnectModel.sf_object_name<heroku_connect.models.HerokuConnectModel.sf_object_name>` has not been set.

``heroku_connect.E002``
~~~~~~~~~~~~~~~~~~~~~~~

:attr:`HerokuConnectModel.sf_access<heroku_connect.models.HerokuConnectModel.sf_access>` must be either ``read_only`` or ``read_write``.

``heroku_connect.E003``
~~~~~~~~~~~~~~~~~~~~~~~

The model has fields with duplicate a :attr:`HerokuConnectFieldMixin.sf_field_name<heroku_connect.models.HerokuConnectFieldMixin.sf_field_name>`.

``heroku_connect.E004``
~~~~~~~~~~~~~~~~~~~~~~~

More than one field is defined as :attr:`HerokuConnectFieldMixin.upsert<heroku_connect.models.HerokuConnectFieldMixin.upsert>`.
