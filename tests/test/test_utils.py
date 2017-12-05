import subprocess

from heroku_connect.test.utils import heroku_cli


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
