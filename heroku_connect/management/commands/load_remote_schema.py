import os
import re
import subprocess

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    Load schema from remote Heroku PostgreSQL database.

    This command can be useful to load the Heroku Connect database schema into
    a local development environment.

    Example::

        python manage.py load_remote_schema --app ninja | psql -a

    .. note::

        This command requires the `Heroku CLI`_ and PostgreSQL_ to be installed.

    .. _`Heroku CLI`: https://cli.heroku.com/
    .. _PostgreSQL: https://www.postgresql.org/

    """

    help = __doc__.strip().splitlines()[0]

    url_pattern = r'postgres://(?P<user>[\d\w]*):(?P<passwd>[\d\w]*)' \
                  r'@(?P<host>[^:]+):(?P<port>\d+)/(?P<dbname>[\d\w]+)'

    def add_arguments(self, parser):
        parser.add_argument('--app', '-a', dest='HEROKU_APP', type=str,
                            help="Heroku app name that the schema will be pulled from.")
        parser.add_argument('--schema', '-s', dest='SCHEMA_NAME', type=str, default='salesforce',
                            help="Name of schema that you want to load.")

    def handle(self, *args, **options):
        heroku_app = options.get('HEROKU_APP')
        schema_name = options['SCHEMA_NAME']
        url = self.get_database_url(heroku_app)
        credentials = self.parse_credentials(url)
        schema = self.get_schema(**credentials, schema_name=schema_name)
        self.stdout.write(schema)

    @staticmethod
    def get_database_url(heroku_app):
        run_args = ['heroku', 'pg:credentials:url']
        if heroku_app:
            run_args += ['-a', heroku_app]

        try:
            output = subprocess.check_output(run_args)
        except subprocess.SubprocessError as e:
            raise CommandError("Please provide the correct Heroku app name.") from e
        else:
            return output.decode('utf-8')

    def parse_credentials(self, url):
        match = re.search(self.url_pattern, url)
        if not match:
            raise CommandError("Could not parse DATABASE_URL.")

        return match.groupdict()

    @staticmethod
    def get_schema(user, host, port, dbname, passwd, schema_name):
        env = os.environ.copy()
        env['PGPASSWORD'] = passwd

        run_args = [
            'pg_dump',
            '-sO',
            '-n', schema_name,
            '-U', user,
            '-h', host,
            '-p', port,
            '-d', dbname,
        ]

        try:
            output = subprocess.check_output(run_args, env=env)
        except subprocess.SubprocessError as e:
            raise CommandError("Schema not found.") from e
        else:
            return output.decode('utf-8')
