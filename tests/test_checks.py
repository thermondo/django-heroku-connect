from django.apps.registry import apps
from django.core import checks

from heroku_connect.checks import _check_foreign_key_target


def test_check_foreign_key_target():
    errors = _check_foreign_key_target(apps)
    assert errors == [checks.Error(
        "testapp.OtherModel.number points to an External ID or the 'sfid', not 'id'.",
        hint="Specify the 'to_field' argument.",
        id='heroku_connect.E005',
    )]
