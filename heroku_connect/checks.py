from django.apps import apps
from django.core.checks import Error

from .db.models import HerokuConnectModel


def _check_foreign_key_target(app_configs, **kwargs):
    errors = []
    all_models = (
        model
        for models in apps.all_models.values()
        for model in models.values()
    )

    for model in all_models:
        opts = model._meta
        relations_to_hc_models = filter(
            lambda f: f.remote_field and issubclass(f.remote_field.model, HerokuConnectModel),
            opts.local_fields
        )

        for field in relations_to_hc_models:
            if 'id' in field.to_fields:
                errors.append(Error(
                    "%s should point to an External ID or the 'sf_id', not 'id'." % field,
                    hint="Specify the 'to_field' argument.",
                    id='heroku_connect.E005',
                ))

    return errors
