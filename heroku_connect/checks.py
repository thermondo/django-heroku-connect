from django.apps import apps
from django.core.checks import Error

from .db.models import HerokuConnectModel
from .utils import get_heroku_connect_models


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


def _check_unique_sf_object_name(app_configs, **kwargs):
    errors = []
    models = set(get_heroku_connect_models())
    unique_models = set({
        model.sf_object_name: model
        for model in models
    }.values())

    for model in models - unique_models:
        errors.append(Error(
            "%s.%s.sf_object_name clashes with another model." % (
                model._meta.app_label, model.__name__),
            hint="Specify a unique 'sf_object_name' argument.",
            id='heroku_connect.E006',
        ))

    return errors
