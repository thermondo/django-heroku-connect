from heroku_connect.db.exceptions import WriteNotSupportedError
from heroku_connect.db.models import READ_ONLY


class HerokuConnectRouter:
    """
    Router that prevents write actions on read-only Heroku Connect tables.

    The router will raise a :class:`.WriteNotSupportedError` error when
    ``save``, ``create``, ``delete``, ``update`` or other model or QuerySet
    methods are called on read-only tables.

    .. note::
        You will need to add the router to your ``DATABASE_ROUTERS`` setting.
        For example::

            DATABASE_ROUTERS = ['heroku_connect.db.router.HerokuConnectRouter']

    .. seealso:: `Automatic database routing`_

    .. _Automatic database routing:
        https://docs.djangoproject.com/en/stable/topics/db/multi-db/#automatic-database-routing

    """

    def db_for_write(self, model, **hints):
        """
        Prevent write actions on read-only tables.

        Raises:
            WriteNotSupportedError: If models.sf_access is ``read_only``.

        """
        try:
            if model.sf_access == READ_ONLY:
                raise WriteNotSupportedError("%r is a read-only model." % model)
        except AttributeError:
            pass
        return None
