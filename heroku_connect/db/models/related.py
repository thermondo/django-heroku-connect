from django.db import models

from heroku_connect.db.models.fields import HerokuConnectFieldMixin

__all__ = ('ConstraintlessForeignObjectMixin', 'Lookup', 'MasterDetail')


class ConstraintlessForeignObjectMixin:
    """Ensure Django does not add foreign key database constraints."""

    def __init__(self, *args, **kwargs):
        kwargs['db_constraint'] = False
        super().__init__(*args, **kwargs)


class Lookup(ConstraintlessForeignObjectMixin, HerokuConnectFieldMixin, models.ForeignKey):
    """Salesforce ``Lookup`` field."""

    pass


class MasterDetail(ConstraintlessForeignObjectMixin, HerokuConnectFieldMixin, models.ForeignKey):
    """Salesforce ``Master-Detail`` field."""

    pass
