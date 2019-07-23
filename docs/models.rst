Models
======

.. autoclass:: heroku_connect.db.models.HerokuConnectModel
    :members:

Model inheritance
-----------------

Model inheritance in with Heroku Connect models is almost identical to
Django's `Model inheritance`_ feature. For example you can build model mixins
as followed:

.. code-block:: python

    from heroku_connect.db import models as hc_models


    class ExternalIDModelMixin(hc_models.HerokuConnectModel):
        sf_access = hc_model.READ_WRITE

        external_id = hc_models.ExternalID(sf_field_name='External_ID__c')

        class Meta:
            abstract = True


    class MyModel(ExternalIDModelMixin):
        sf_object_name = 'My_Object__c'

        data = hc_models.Text(sf_field_name='Data__c')

.. _`Model inheritance`: https://docs.djangoproject.com/en/stable/topics/db/models/#model-inheritance

Multi-table inheritance
-----------------------

`Multi-table inheritance`_ is a concept where each superclass is a model by
itself. It allows building hybrid models that are partly managed by Heroku
Connect partly by Django.

Example:

.. code-block:: python

    from django.db import models
    from heroku_connect.db import models as hc_models


    class SFObjectModel(hc_models.HerokuConnectModel):
        sf_object_name = 'My_Object__c'
        sf_access = hc_model.READ_WRITE

        external_id = hc_models.ExternalID(sf_field_name='External_ID__c')
        data = hc_models.Text(sf_field_name='Data__c')


    class CompoundModel(SFObjectModel):
        hc_model = models.OneToOneField(SFObjectModel, on_delete=models.CASCADE,
                                        to_field='external_id', parent_link=True,
                                        db_constraint=False)
        more_data = models.TextField()
        
        class Meta:
            managed = True

In this scenario ``SFObjectModel`` is managed by Heroku Connect and ``CompoundModel``
a hybrid where ``CompoundModel.data`` is manged by Heroku Connect and
``CompoundModel.more_data`` is managed by Django.


.. Warning::
    You should use your own ``parent_link``
    :class:`OneToOneField<django.db.models.OneToOneField>` that points to the
    ``upsert``-field of your parent Heroku Connect model as the ``id``-field
    is not not guarantied in to be consistent.

It is also possible to have two concrete Heroku Connect models to Inherit from
each other.

.. _`Multi-table inheritance`: https://docs.djangoproject.com/en/stable/topics/db/models/#multi-table-inheritance
