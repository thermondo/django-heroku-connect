from collections import defaultdict

from django.apps import apps
from django.core.checks import Error, Warning
from django.db.models.fields.related import (
    ForeignKey, ManyToManyField, RelatedField
)

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
        fks_to_hc_model = filter(
            lambda f: isinstance(f, (ForeignKey, ManyToManyField)) and
            issubclass(f.remote_field.model, HerokuConnectModel),
            opts.local_fields
        )

        m2ms_to_hc_model = filter(
            lambda f: issubclass(f.remote_field.model, HerokuConnectModel),
            opts.local_many_to_many
        )

        for field in fks_to_hc_model:
            errors.extend(_check_foreign_key_target(field))
            errors.extend(_check_foreign_key_constraint(field))

        for field in m2ms_to_hc_model:
            errors.extend(_check_many_to_many_target(field))
            errors.extend(_check_many_to_many_constraint(field))

    return errors


def _check_foreign_key_target(field):
    errors = []
    if field.target_field.name == 'id':
        errors.append(Error(
            "%s should point to an External ID or the 'sf_id', not 'id'." % field,
            hint="Specify the 'to_field' argument.",
            id='heroku_connect.E005',
        ))
    return errors


def _check_many_to_many_target(field):
    errors = []
    if field.target_field.name == 'id':
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


def _check_many_to_many_constraint(field):
    warnings = []
    if field.remote_field.db_constraint:
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
