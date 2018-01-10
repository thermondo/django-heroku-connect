import pytest
from django.apps.registry import apps
from django.core import checks
from django.core.management import call_command
from django.core.management.base import SystemCheckError

from heroku_connect.checks import _check_foreign_key_target


def test_check_foreign_key_target():
    errors = _check_foreign_key_target(apps)
    assert errors == [checks.Error(
        "testapp.OtherModel.number should point to an External ID or the 'sf_id', not 'id'.",
        hint="Specify the 'to_field' argument.",
        id='heroku_connect.E005',
    )]


def test_django_check():
    with pytest.raises(SystemCheckError):
        call_command('check')
