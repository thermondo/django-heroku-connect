from django.core.management import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections

from heroku_connect.conf import settings
from heroku_connect.utils import create_heroku_connect_schema


class Command(BaseCommand):
    """Create Heroku Connect schema for local development."""

    help = __doc__.strip().splitlines()[0]

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            dest="force",
            help="Delete existing schema.",
        )
        parser.add_argument(
            "--database",
            action="store",
            dest="database",
            default=DEFAULT_DB_ALIAS,
            help='Nominates a database to synchronize. Defaults to the "default" '
            "database.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        force = options["force"]
        schema = settings.HEROKU_CONNECT_SCHEMA
        if force:
            connection = connections[db]
            with connection.cursor() as cursor:
                cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE;")
        if not create_heroku_connect_schema(using=db):
            raise CommandError(f"Schema {schema} already exists.")
        self.stdout.write(f"Schema {schema} created.")
