from collections import defaultdict

from django.apps import apps
from django.core.checks import Error, Warning

from .db.models import HerokuConnectModel
from .utils import get_heroku_connect_models


def _check_foreign_key(app_configs, **kwargs):
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
            errors.extend(_check_foreign_key_target(field))
            errors.extend(_check_foreign_key_constraint(field))

    return errors


def _check_foreign_key_target(field):
    errors = []
    try:
        if field.target_field.name == 'id':
            errors.append(Error(
                "%s should point to an External ID or the 'sf_id', not 'id'." % field,
                hint="Specify the 'to_field' argument.",
                id='heroku_connect.E005',
            ))
    except AttributeError:
        if 'id' in field.to_fields:
            errors.append(Error(
                "%s should point to an External ID or the 'sf_id', not 'id'." % field,
                hint="Specify the 'to_field' argument.",
                id='heroku_connect.E005',
            ))
    return errors


def _check_foreign_key_constraint(field):
    warnings = []
    if field.db_constraint:
        warnings.append(Warning(
            "%s should not have database constraints to a Heroku Connect model." % field,
            hint="Set 'db_constraint' to False.",
            id='heroku_connect.W001',
        ))
    return warnings


def _check_unique_sf_object_name(app_configs, **kwargs):
    errors = []
    model_map = defaultdict(list)
    for model in get_heroku_connect_models():
        model_map[model.sf_object_name].append(model)

    for sf_object_name, models in model_map.items():
        if len(models) > 1:
            for model in models:
                errors.append(Error(
                    "%s.%s.sf_object_name '%s' clashes with another model." % (
                        model._meta.app_label, model.__name__, sf_object_name),
                    hint="Make sure your 'sf_object_name' is correct.",
                    id='heroku_connect.E006',
                    obj=model
                ))

    return errors
