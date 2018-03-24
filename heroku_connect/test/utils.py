"""Test utilities for Django and Heroku Connect."""
import copy
import os
import shlex
import stat
import tempfile
from contextlib import contextmanager

from django.test import override_settings

__all__ = ('heroku_cli', 'no_heroku_connect_write_restrictions')


@contextmanager
def heroku_cli(stdout='', stderr='', exit_code=0):
    r"""
    Context manager to mock the Heroku CLI command.

    Example::

        import subprocess
        from heroku_connect.test.utils import heroku_cli

        with heroku_cli(stdout='success', stderr='warning', exit=0):
            process = subprocess.run(
                ['heroku'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        assert process.returncode == 0
        assert process.stdout == b'success\n'
        assert process.stderr == b'warning\n'

    Args:
        stdout (str): String the command writes to ``stdout``.
        stderr (str): String the command writes to ``stderr``.
        exit_code (int): Code that the command will exit with, default ``1``.

    """
    bin_dir = tempfile.mkdtemp()
    path = os.environ.get('PATH', '')
    os.environ['PATH'] = ':'.join([bin_dir, path])
    exec_name = os.path.join(bin_dir, 'heroku')
    script = (
        '#!/bin/bash\n'
        'echo %s 1>&1\n'
        'echo %s 1>&2\n'
        'exit %i\n'
    )
    script %= (
        shlex.quote(stdout), shlex.quote(stderr), exit_code
    )
    with open(exec_name, 'wb+') as f:
        f.seek(0)
        f.write(script.encode('utf-8'))
    st = os.stat(exec_name)
    os.chmod(exec_name, st.st_mode | stat.S_IEXEC)
    yield
    os.environ['PATH'] = path


@contextmanager
def no_heroku_connect_write_restrictions():
    """
    Allow writing to read-only Heroku Connect tables.

    Can be used to create test data, e.g.::

        def get_test_data():
            with no_heroku_connect_write_restrictions():
                return MyReadOnlyModel.objects.create()

    """
    from ..conf import settings
    new_settings = copy.copy(getattr(settings, 'DATABASE_ROUTERS', []))
    try:
        new_settings.remove('heroku_connect.db.router.HerokuConnectRouter')
    except ValueError:
        pass
    with override_settings(DATABASE_ROUTERS=new_settings):
        yield
