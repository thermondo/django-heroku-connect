import subprocess

import pytest
from django.test import override_settings
from django.utils import timezone

from heroku_connect.db import models as hc_models
from heroku_connect.db.exceptions import WriteNotSupportedError
from heroku_connect.test.utils import (
    heroku_cli, no_heroku_connect_write_restrictions
)
from tests.testapp.models import ReadOnlyModel


class TestHerokuCLI:
    def test_no_args(self):
        with heroku_cli():
            process = subprocess.run(['heroku'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert process.returncode == 0
        assert process.stdout == b'\n'
        assert process.stderr == b'\n'

    def test_exit_code(self):
        with heroku_cli(exit_code=1):
            process = subprocess.run(['heroku'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert process.returncode == 1
        assert process.stdout == b'\n'
        assert process.stderr == b'\n'

    def test_stdout(self):
        with heroku_cli(stdout='I am Batman'):
            process = subprocess.run(['heroku'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert process.returncode == 0
        assert process.stdout == b'I am Batman\n'
        assert process.stderr == b'\n'

    def test_stderr(self):
        with heroku_cli(stderr='I am Batman'):
            process = subprocess.run(['heroku'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert process.returncode == 0
        assert process.stdout == b'\n'
        assert process.stderr == b'I am Batman\n'

    def test_escaping(self):
        with heroku_cli(stdout='""; echo "foo"', stderr='""; echo "foo"'):
            process = subprocess.run(['heroku'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert process.stdout == b'""; echo "foo"\n'
        assert process.stderr == b'""; echo "foo"\n'


class BogusRouter:
    _did_run = False

    def db_for_write(self, model, **hints):
        BogusRouter._did_run = True


class TestNoHerokuConnectWriteRestrictions:
    def test_write(self, db):
        data_instance = ReadOnlyModel()
        with no_heroku_connect_write_restrictions():
            data_instance.save()

        # should raise an error outside the context manager
        with pytest.raises(WriteNotSupportedError):
            data_instance.delete()

    @override_settings(DATABASE_ROUTERS=[])
    def test_no_router(self, db):
        data_instance = ReadOnlyModel()
        with no_heroku_connect_write_restrictions():
            data_instance.save()

        # should not raise and restore empty setting
        data_instance.delete()

    @override_settings(DATABASE_ROUTERS=[
        'tests.test.test_utils.BogusRouter',
        'heroku_connect.db.router.HerokuConnectRouter',
    ])
    def test_other_routers(self, db):
        data_instance = ReadOnlyModel()
        assert not BogusRouter._did_run
        with no_heroku_connect_write_restrictions():
            data_instance.save()

        assert BogusRouter._did_run

        # should raise an error outside the context manager
        BogusRouter._did_run = False
        with pytest.raises(WriteNotSupportedError):
            data_instance.delete()

        assert BogusRouter._did_run
