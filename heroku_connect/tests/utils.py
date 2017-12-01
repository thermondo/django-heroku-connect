"""Test utilities for Django and Heroku Connect."""
import os
import stat
import tempfile
from contextlib import contextmanager


@contextmanager
def heroku_cli(stdout=b'', stderr=b'', exit_code=0):
    """
    Context manager to mock the Heroku CLI command.

    Example::

        import subprocess
        from heroku_connect.tests.utils import heroku_cli

        with heroku_cli(stdout=b'success', stderr=b'warning', exit=0):
            output = subprocess.check_output(['heroku'])
        assert output == 'success'

    Args:
        stdout (bytes): String the command writes to ``stdout``.
        stderr (bytes): String the command writes to ``stderr``.
        exit_code (int): Code that the command will exit with, default ``1``.

    """
    bin_dir = tempfile.mkdtemp()
    path = os.environ.get('PATH', '')
    os.environ['PATH'] = ':'.join([bin_dir, path])
    exec_name = os.path.join(bin_dir, 'heroku')
    with open(exec_name, 'wb+') as f:
        f.seek(0)
        f.write(
            b'#!/bin/bash\n'
            b'echo %b\n'
            b'echo %b\n'
            b'exit %i\n'
            % (
                stdout, stderr, exit_code
            )
        )
    os.system('cat %s' % exec_name)
    st = os.stat(exec_name)
    os.chmod(exec_name, st.st_mode | stat.S_IEXEC)
    yield
    os.environ['PATH'] = path
